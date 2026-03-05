"""
Sync and collection API routes
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

router = APIRouter(prefix="/api", tags=["sync"])


class SyncRequest(BaseModel):
    library_id: str
    api_key: str
    collection_keys: Optional[List[str]] = Field(default=None)


@router.post("/sync")
async def sync_papers(request: SyncRequest):
    """Sync new papers from Zotero library.

    If collection_keys is provided, only papers in those collections
    (and their sub-collections) will be synced.
    """
    from main import config, zotero_monitor, processing_queue
    from services.zotero_monitor import ZoteroMonitor
    import main as main_module

    try:
        if request.library_id and request.api_key:
            config.zotero_library_id = request.library_id
            config.zotero_api_key = request.api_key
            main_module.zotero_monitor = ZoteroMonitor(config)

        zm = main_module.zotero_monitor
        zm.fetch_collections()
        new_items = zm.fetch_new_items(collection_keys=request.collection_keys)

        for item in new_items:
            await processing_queue.put(item)

        return {
            "status": "success",
            "new_papers": new_items,
            "count": len(new_items),
            "message": f"Found {len(new_items)} new papers. Processing in background.",
        }

    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections")
async def get_collections():
    """Get Zotero collection structure"""
    from main import zotero_monitor

    try:
        collections = zotero_monitor.fetch_collections()
        return {
            "status": "success",
            "collections": collections,
            "count": len(collections),
        }
    except Exception as e:
        logger.error(f"Collections fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
