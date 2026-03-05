"""
Main FastAPI application for Zotero-Obsidian AI integration
"""

import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from dotenv import load_dotenv

from services.zotero_monitor import ZoteroMonitor
from services.bedrock_processor import BedrockProcessor
from services.cache import RedisCache
from utils.config import Config

from api.papers import router as papers_router
from api.sync import router as sync_router
from api.prompts import router as prompts_router

# Load environment variables
load_dotenv()


# Global instances
config = Config()
zotero_monitor: Optional[ZoteroMonitor] = None
bedrock_processor: Optional[BedrockProcessor] = None
cache: Optional[RedisCache] = None
processing_queue = asyncio.Queue()
active_collection_keys: Optional[list] = None  # Set by plugin to filter collections


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global zotero_monitor, bedrock_processor, cache

    logger.info("Starting Zotero-Obsidian AI Backend...")

    # Initialize services
    zotero_monitor = ZoteroMonitor(config)
    bedrock_processor = BedrockProcessor(config)

    # Initialize Redis cache (non-fatal if unavailable)
    cache = RedisCache(config)
    try:
        if cache.available:
            logger.info("Redis cache connected")
    except Exception:
        logger.warning("Redis unavailable — running without cache")
        cache = None

    # Start background processing task
    asyncio.create_task(process_paper_queue())

    # Start Zotero monitor in background if API key is configured
    if config.zotero_api_key:
        asyncio.create_task(monitor_zotero_background())

    yield

    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Zotero-Obsidian AI Backend",
    description="Intelligent research paper processing service",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for Obsidian plugin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(papers_router)
app.include_router(sync_router)
app.include_router(prompts_router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Zotero-Obsidian AI Backend",
        "redis": cache.available if cache else False,
        "timestamp": datetime.now().isoformat(),
    }


async def process_paper_queue():
    """Background task to process papers from queue"""
    while True:
        try:
            paper_data = await processing_queue.get()
            logger.info(f"Processing paper: {paper_data['title'][:50]}...")

            # Download PDF if available
            pdf_path = None
            if paper_data.get("attachments"):
                for attachment in paper_data["attachments"]:
                    pdf_path = zotero_monitor.download_pdf(
                        paper_data["zotero_key"], attachment["key"]
                    )
                    if pdf_path:
                        break

            # Check analysis cache
            if cache and cache.available:
                cached_analysis = cache.get_analysis(paper_data["zotero_key"])
                if cached_analysis:
                    logger.info(f"Using cached analysis for: {paper_data['title'][:50]}")
                    zotero_monitor.mark_as_processed(paper_data["zotero_key"])
                    continue

            # Process with Bedrock
            analysis_result = await bedrock_processor.analyze_paper(paper_data, pdf_path)

            # Cache the analysis
            if cache and cache.available:
                cache.cache_analysis(paper_data["zotero_key"], analysis_result)
                cache.cache_paper(paper_data["zotero_key"], paper_data)

            # Find connections with existing papers
            existing_notes = []  # Would be fetched from database
            if existing_notes:
                connections = await bedrock_processor.find_connections(
                    paper_data, existing_notes
                )
                analysis_result["connections"] = connections

            zotero_monitor.mark_as_processed(paper_data["zotero_key"])
            logger.info(f"Successfully processed: {paper_data['title'][:50]}...")

        except Exception as e:
            logger.error(f"Queue processing error: {e}")
            await asyncio.sleep(5)


async def monitor_zotero_background():
    """Background task to monitor Zotero for changes"""

    def process_callback(item):
        asyncio.create_task(processing_queue.put(item))

    await asyncio.to_thread(
        zotero_monitor.monitor_loop,
        callback=process_callback,
        interval=config.sync_interval,
        collection_keys=active_collection_keys,
    )


if __name__ == "__main__":
    import uvicorn

    logger.add(
        Path(config.data_dir).parent / "logs" / "backend.log",
        rotation="10 MB",
        retention="30 days",
        level="INFO",
    )

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
