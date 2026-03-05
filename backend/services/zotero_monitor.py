"""
Zotero Library Monitor Service
Monitors Zotero library for new papers and maintains collection structure
"""

import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from pathlib import Path

from pyzotero import zotero
from loguru import logger
from sqlalchemy import create_engine, text
from tenacity import retry, stop_after_attempt, wait_exponential

from models.paper import Paper, ProcessingStatus
from utils.config import Config


class ZoteroMonitor:
    """Monitors Zotero library for changes and maintains collection structure"""

    def __init__(self, config: Config):
        self.config = config
        self.library_id = config.zotero_library_id
        self.library_type = config.zotero_library_type  # 'user' or 'group'
        self.api_key = config.zotero_api_key

        # Initialize Zotero client
        self.zot = zotero.Zotero(self.library_id, self.library_type, self.api_key)

        # Track processed items
        self.processed_items: Set[str] = self._load_processed_items()

        # Collection mapping for maintaining library structure
        self.collection_map: Dict[str, Dict] = {}

        # Initialize database connection
        self.db_path = Path(config.data_dir) / "zotero_cache.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self._init_db()

    def _init_db(self):
        """Initialize database for tracking processed papers"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS papers (
                    zotero_key TEXT PRIMARY KEY,
                    title TEXT,
                    authors TEXT,
                    year INTEGER,
                    collection_path TEXT,
                    file_path TEXT,
                    processed_at TIMESTAMP,
                    status TEXT,
                    metadata TEXT
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS collections (
                    key TEXT PRIMARY KEY,
                    name TEXT,
                    parent_key TEXT,
                    path TEXT,
                    updated_at TIMESTAMP
                )
            """))
            conn.commit()

    def _load_processed_items(self) -> Set[str]:
        """Load set of already processed item keys"""
        cache_file = Path(self.config.data_dir) / "processed" / "items.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return set(json.load(f))
        return set()

    def _save_processed_items(self):
        """Save processed item keys to disk"""
        cache_file = Path(self.config.data_dir) / "processed" / "items.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(list(self.processed_items), f, indent=2)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def fetch_collections(self) -> Dict[str, Dict]:
        """Fetch and map all collections maintaining hierarchy"""
        logger.info("Fetching Zotero collections...")
        collections = self.zot.collections()

        # Build collection hierarchy
        collection_map = {}
        for coll in collections:
            key = coll['key']
            collection_map[key] = {
                'name': coll['data']['name'],
                'parent': coll['data'].get('parentCollection', None),
                'key': key,
                'path': None  # Will be computed
            }

        # Compute full paths for each collection
        for key, coll in collection_map.items():
            coll['path'] = self._get_collection_path(key, collection_map)

            # Store in database
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT OR REPLACE INTO collections (key, name, parent_key, path, updated_at)
                    VALUES (:key, :name, :parent_key, :path, :updated_at)
                """), {
                    'key': key,
                    'name': coll['name'],
                    'parent_key': coll['parent'],
                    'path': coll['path'],
                    'updated_at': datetime.now()
                })
                conn.commit()

        self.collection_map = collection_map
        logger.info(f"Fetched {len(collection_map)} collections")
        return collection_map

    def _get_collection_path(self, key: str, collection_map: Dict) -> str:
        """Recursively build full collection path"""
        if key not in collection_map:
            return ""

        coll = collection_map[key]
        if coll['parent'] is None:
            return coll['name']

        parent_path = self._get_collection_path(coll['parent'], collection_map)
        return f"{parent_path}/{coll['name']}" if parent_path else coll['name']

    def fetch_new_items(self, limit: int = 100, collection_keys: Optional[List[str]] = None) -> List[Dict]:
        """Fetch new items from Zotero that haven't been processed.

        Args:
            limit: Maximum number of items to fetch.
            collection_keys: If provided, only return items belonging to these
                collection keys (or their sub-collections).
        """
        logger.info("Checking for new items in Zotero...")

        # Build set of allowed collection keys (including children)
        allowed_collections: Optional[Set[str]] = None
        if collection_keys:
            allowed_collections = self._expand_collection_keys(collection_keys)
            logger.info(f"Filtering to {len(allowed_collections)} collections (incl. children)")

        # Get items modified in last N days (configurable)
        since_date = (datetime.now() - timedelta(days=self.config.sync_days_back)).strftime('%Y-%m-%d')
        items = self.zot.items(q='', since=since_date, limit=limit)

        new_items = []
        for item in items:
            item_key = item['key']
            item_type = item['data'].get('itemType', '')

            # Only process journal articles, conference papers, books, preprints
            if item_type not in ['journalArticle', 'conferencePaper', 'book', 'preprint', 'thesis', 'report']:
                continue

            if item_key in self.processed_items:
                continue

            # Collection filtering
            item_collections = item['data'].get('collections', [])
            if allowed_collections is not None:
                if not any(ck in allowed_collections for ck in item_collections):
                    continue

            # Get collection paths for this item
            collection_paths = [
                self.collection_map.get(coll_key, {}).get('path', 'Uncategorized')
                for coll_key in item_collections
            ]

            # Extract paper metadata
            paper_data = self._extract_paper_data(item, collection_paths)
            if paper_data:
                new_items.append(paper_data)
                logger.info(f"Found new paper: {paper_data['title'][:50]}...")

        logger.info(f"Found {len(new_items)} new items to process")
        return new_items

    def _expand_collection_keys(self, keys: List[str]) -> Set[str]:
        """Given a list of collection keys, return the set including all children."""
        result = set(keys)
        changed = True
        while changed:
            changed = False
            for key, coll in self.collection_map.items():
                if key not in result and coll.get('parent') in result:
                    result.add(key)
                    changed = True
        return result

    def _extract_paper_data(self, item: Dict, collection_paths: List[str]) -> Optional[Dict]:
        """Extract relevant data from Zotero item"""
        data = item['data']

        paper = {
            'zotero_key': item['key'],
            'title': data.get('title', 'Untitled'),
            'authors': self._extract_authors(data.get('creators', [])),
            'abstract': data.get('abstractNote', ''),
            'year': data.get('date', '').split('-')[0] if data.get('date') else None,
            'doi': data.get('DOI', ''),
            'url': data.get('url', ''),
            'tags': [tag['tag'] for tag in data.get('tags', [])],
            'collections': collection_paths,
            'item_type': data.get('itemType', 'article'),
            'publication': data.get('publicationTitle', ''),
            'volume': data.get('volume', ''),
            'issue': data.get('issue', ''),
            'pages': data.get('pages', ''),
            'extra': data.get('extra', ''),
            'attachments': [],
            'notes': []
        }

        # Check for PDF attachments
        if item.get('links', {}).get('attachment'):
            attachments = self.zot.children(item['key'])
            for attachment in attachments:
                if attachment['data'].get('contentType') == 'application/pdf':
                    paper['attachments'].append({
                        'key': attachment['key'],
                        'title': attachment['data'].get('title', ''),
                        'filename': attachment['data'].get('filename', ''),
                        'md5': attachment['data'].get('md5', '')
                    })

        # Get notes
        notes = [n for n in self.zot.children(item['key'])
                 if n['data'].get('itemType') == 'note']
        paper['notes'] = [n['data'].get('note', '') for n in notes]

        return paper

    def _extract_authors(self, creators: List[Dict]) -> str:
        """Extract author names from creators list"""
        authors = []
        for creator in creators:
            if creator.get('creatorType') == 'author':
                first = creator.get('firstName', '')
                last = creator.get('lastName', '')
                name = f"{first} {last}".strip() if first or last else creator.get('name', '')
                if name:
                    authors.append(name)
        return "; ".join(authors)

    def download_pdf(self, item_key: str, attachment_key: str) -> Optional[Path]:
        """Download PDF attachment for a paper"""
        try:
            output_dir = Path(self.config.data_dir) / "cache" / "pdfs"
            output_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{item_key}_{attachment_key}.pdf"
            output_path = output_dir / filename

            if output_path.exists():
                logger.info(f"PDF already cached: {filename}")
                return output_path

            # Download the file
            logger.info(f"Downloading PDF: {filename}")
            self.zot.dump(attachment_key, f"{output_path}")

            if output_path.exists():
                logger.info(f"Successfully downloaded: {filename}")
                return output_path
            else:
                logger.error(f"Failed to download PDF: {filename}")
                return None

        except Exception as e:
            logger.error(f"Error downloading PDF {attachment_key}: {e}")
            return None

    def mark_as_processed(self, item_key: str, status: str = "completed"):
        """Mark an item as processed"""
        self.processed_items.add(item_key)
        self._save_processed_items()

        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE papers SET status = :status, processed_at = :processed_at
                WHERE zotero_key = :key
            """), {
                'key': item_key,
                'status': status,
                'processed_at': datetime.now()
            })
            conn.commit()

    def get_paper_by_key(self, item_key: str) -> Optional[Dict]:
        """Retrieve paper metadata by Zotero key"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM papers WHERE zotero_key = :key
            """), {'key': item_key}).fetchone()

            if result:
                return dict(result)
        return None

    def monitor_loop(self, callback=None, interval: int = 300, collection_keys: Optional[List[str]] = None):
        """Main monitoring loop - checks for new papers periodically"""
        logger.info(f"Starting Zotero monitor (checking every {interval} seconds)...")

        while True:
            try:
                # Update collections
                self.fetch_collections()

                # Check for new items
                new_items = self.fetch_new_items(collection_keys=collection_keys)

                if new_items and callback:
                    for item in new_items:
                        try:
                            callback(item)
                        except Exception as e:
                            logger.error(f"Error processing item {item['zotero_key']}: {e}")

                # Wait before next check
                time.sleep(interval)

            except KeyboardInterrupt:
                logger.info("Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(interval)