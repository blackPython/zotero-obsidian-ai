"""
Paper-related API routes
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api", tags=["papers"])


class QARequest(BaseModel):
    zotero_key: str
    question: str
    context: Optional[str] = ""


class CustomAnalysisRequest(BaseModel):
    zotero_key: str
    analysis_type: str
    additional_context: Optional[dict] = {}


@router.get("/paper/{zotero_key}")
async def get_paper(zotero_key: str):
    """Get details for a specific paper"""
    from main import zotero_monitor, cache

    try:
        # Try cache first
        if cache and cache.available:
            cached = cache.get_paper(zotero_key)
            if cached:
                return {"status": "success", "paper": cached, "source": "cache"}

        paper_data = zotero_monitor.get_paper_by_key(zotero_key)
        if not paper_data:
            raise HTTPException(status_code=404, detail="Paper not found")

        # Cache for next time
        if cache and cache.available:
            cache.cache_paper(zotero_key, paper_data)

        return {"status": "success", "paper": paper_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Paper fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qa")
async def answer_question(request: QARequest):
    """Answer a question about a specific paper"""
    from main import zotero_monitor, bedrock_processor, cache

    try:
        # Check Q&A cache
        if cache and cache.available:
            cached_answer = cache.get_qa(request.zotero_key, request.question)
            if cached_answer:
                return {
                    "status": "success",
                    "answer": cached_answer,
                    "source": "cache",
                    "timestamp": datetime.now().isoformat(),
                }

        # Get paper data
        paper_data = zotero_monitor.get_paper_by_key(request.zotero_key)
        if not paper_data:
            item = zotero_monitor.zot.item(request.zotero_key)
            paper_data = zotero_monitor._extract_paper_data(item, [])

        if not paper_data:
            raise HTTPException(status_code=404, detail="Paper not found")

        answer = await bedrock_processor.answer_question(
            paper_data, request.question, request.context
        )

        # Cache the answer
        if cache and cache.available:
            cache.cache_qa(request.zotero_key, request.question, answer)

        return {
            "status": "success",
            "answer": answer,
            "paper_title": paper_data.get("title", "Unknown"),
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Q&A error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/custom-analysis")
async def run_custom_analysis(request: CustomAnalysisRequest):
    """Run custom analysis on a paper"""
    from main import zotero_monitor, bedrock_processor

    try:
        paper_data = zotero_monitor.get_paper_by_key(request.zotero_key)
        if not paper_data:
            raise HTTPException(status_code=404, detail="Paper not found")

        result = await bedrock_processor.custom_analysis(
            paper_data, request.analysis_type, **request.additional_context
        )

        return {
            "status": "success",
            "analysis": result,
            "analysis_type": request.analysis_type,
            "timestamp": datetime.now().isoformat(),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Custom analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paper/{zotero_key}/analysis")
async def get_paper_analysis(zotero_key: str):
    """Get the analysis results for a processed paper"""
    from main import cache

    try:
        if cache and cache.available:
            analysis = cache.get_analysis(zotero_key)
            if analysis:
                return {"status": "success", "analysis": analysis}

        return {"status": "pending", "message": "Analysis not yet available"}

    except Exception as e:
        logger.error(f"Analysis fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reprocess/{zotero_key}")
async def reprocess_paper(zotero_key: str):
    """Reprocess a paper with updated prompts"""
    from main import zotero_monitor, processing_queue, cache

    try:
        # Remove from processed items
        if zotero_key in zotero_monitor.processed_items:
            zotero_monitor.processed_items.remove(zotero_key)
            zotero_monitor._save_processed_items()

        # Invalidate cache
        if cache and cache.available:
            cache.invalidate_paper(zotero_key)

        # Fetch paper data
        item = zotero_monitor.zot.item(zotero_key)
        paper_data = zotero_monitor._extract_paper_data(item, [])

        if not paper_data:
            raise HTTPException(status_code=404, detail="Paper not found")

        await processing_queue.put(paper_data)

        return {
            "status": "success",
            "message": "Paper queued for reprocessing",
            "zotero_key": zotero_key,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reprocess error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
