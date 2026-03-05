"""
Data models for paper processing
"""

from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ProcessingStatus(Enum):
    """Paper processing status"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class Paper(BaseModel):
    """Paper data model"""

    # Zotero metadata
    zotero_key: str
    title: str
    authors: str
    abstract: Optional[str] = ""
    year: Optional[int] = None
    doi: Optional[str] = ""
    url: Optional[str] = ""

    # Organization
    collections: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    # Publication details
    item_type: str = "article"
    publication: Optional[str] = ""
    volume: Optional[str] = ""
    issue: Optional[str] = ""
    pages: Optional[str] = ""

    # Files and content
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    pdf_path: Optional[str] = None
    full_text: Optional[str] = None

    # Processing metadata
    status: ProcessingStatus = ProcessingStatus.PENDING
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    # Analysis results
    analysis: Optional[Dict[str, Any]] = None
    connections: Optional[Dict[str, Any]] = None
    embeddings: Optional[List[float]] = None

    model_config = ConfigDict(use_enum_values=True)