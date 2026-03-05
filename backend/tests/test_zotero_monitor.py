"""
Tests for services/zotero_monitor.py (with mocked Zotero API)
"""

import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def monitor(mock_config):
    """Create a ZoteroMonitor with mocked pyzotero client"""
    with patch("services.zotero_monitor.zotero") as mock_zotero_mod:
        mock_zot = MagicMock()
        mock_zotero_mod.Zotero.return_value = mock_zot

        from services.zotero_monitor import ZoteroMonitor

        zm = ZoteroMonitor(mock_config)
        zm.zot = mock_zot
        yield zm, mock_zot


def test_init(monitor):
    zm, _ = monitor
    assert zm.library_type == "user"
    assert isinstance(zm.processed_items, set)


def test_extract_authors(monitor):
    zm, _ = monitor
    creators = [
        {"creatorType": "author", "firstName": "Alice", "lastName": "Smith"},
        {"creatorType": "author", "firstName": "Bob", "lastName": "Jones"},
        {"creatorType": "editor", "firstName": "Eve", "lastName": "Admin"},
    ]
    result = zm._extract_authors(creators)
    assert "Alice Smith" in result
    assert "Bob Jones" in result
    assert "Eve Admin" not in result


def test_get_collection_path(monitor):
    zm, _ = monitor
    collection_map = {
        "A": {"name": "Science", "parent": None},
        "B": {"name": "Physics", "parent": "A"},
        "C": {"name": "Quantum", "parent": "B"},
    }
    assert zm._get_collection_path("A", collection_map) == "Science"
    assert zm._get_collection_path("B", collection_map) == "Science/Physics"
    assert zm._get_collection_path("C", collection_map) == "Science/Physics/Quantum"


def test_processed_items_round_trip(monitor, mock_config):
    zm, _ = monitor
    zm.mark_as_processed("KEY1")
    assert "KEY1" in zm.processed_items

    # Verify file was written
    cache_file = mock_config.data_dir / "processed" / "items.json"
    assert cache_file.exists()
    with open(cache_file) as f:
        items = json.load(f)
    assert "KEY1" in items


def test_fetch_collections(monitor):
    zm, mock_zot = monitor
    mock_zot.collections.return_value = [
        {"key": "C1", "data": {"name": "ML", "parentCollection": None}},
        {"key": "C2", "data": {"name": "NLP", "parentCollection": "C1"}},
    ]
    result = zm.fetch_collections()
    assert "C1" in result
    assert result["C1"]["path"] == "ML"
    assert result["C2"]["path"] == "ML/NLP"


def test_fetch_new_items_filters_types(monitor, sample_paper):
    zm, mock_zot = monitor
    zm.collection_map = {}

    # One valid item + one attachment (should be skipped)
    mock_zot.items.return_value = [
        {
            "key": "P1",
            "data": {
                "itemType": "journalArticle",
                "title": "Test Paper",
                "creators": [],
                "collections": [],
                "date": "2024-01-01",
            },
            "links": {},
        },
        {
            "key": "P2",
            "data": {
                "itemType": "attachment",
                "title": "PDF",
            },
            "links": {},
        },
    ]

    # Mock _extract_paper_data to return a simple dict
    zm._extract_paper_data = MagicMock(return_value={"zotero_key": "P1", "title": "Test"})

    items = zm.fetch_new_items()
    assert len(items) == 1
    assert items[0]["zotero_key"] == "P1"


def test_fetch_new_items_filters_by_collection(monitor):
    zm, mock_zot = monitor
    zm.collection_map = {
        "C1": {"name": "ML", "parent": None, "key": "C1", "path": "ML"},
        "C2": {"name": "NLP", "parent": "C1", "key": "C2", "path": "ML/NLP"},
        "C3": {"name": "Biology", "parent": None, "key": "C3", "path": "Biology"},
    }

    mock_zot.items.return_value = [
        {
            "key": "P1",
            "data": {
                "itemType": "journalArticle",
                "title": "ML Paper",
                "creators": [],
                "collections": ["C2"],
                "date": "2024-01-01",
            },
            "links": {},
        },
        {
            "key": "P2",
            "data": {
                "itemType": "journalArticle",
                "title": "Bio Paper",
                "creators": [],
                "collections": ["C3"],
                "date": "2024-01-01",
            },
            "links": {},
        },
        {
            "key": "P3",
            "data": {
                "itemType": "journalArticle",
                "title": "Uncategorized Paper",
                "creators": [],
                "collections": [],
                "date": "2024-01-01",
            },
            "links": {},
        },
    ]

    zm._extract_paper_data = MagicMock(side_effect=lambda item, paths: {
        "zotero_key": item["key"],
        "title": item["data"]["title"],
    })

    # Filter to C1 (ML) — should include C2 (NLP) as child, exclude C3 and uncategorized
    items = zm.fetch_new_items(collection_keys=["C1"])
    assert len(items) == 1
    assert items[0]["zotero_key"] == "P1"

    # No filter — should return all 3
    zm.processed_items = set()
    items = zm.fetch_new_items(collection_keys=None)
    assert len(items) == 3


def test_expand_collection_keys(monitor):
    zm, _ = monitor
    zm.collection_map = {
        "C1": {"name": "ML", "parent": None},
        "C2": {"name": "NLP", "parent": "C1"},
        "C3": {"name": "Transformers", "parent": "C2"},
        "C4": {"name": "Biology", "parent": None},
    }
    expanded = zm._expand_collection_keys(["C1"])
    assert expanded == {"C1", "C2", "C3"}


def test_download_pdf_cached(monitor, mock_config):
    zm, mock_zot = monitor
    # Create a "cached" PDF
    pdf_dir = mock_config.data_dir / "cache" / "pdfs"
    cached = pdf_dir / "KEY1_ATT1.pdf"
    cached.write_text("fake pdf")

    result = zm.download_pdf("KEY1", "ATT1")
    assert result == cached
    mock_zot.dump.assert_not_called()
