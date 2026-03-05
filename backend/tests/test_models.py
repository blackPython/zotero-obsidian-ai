"""
Tests for models/paper.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.paper import Paper, ProcessingStatus


def test_processing_status_values():
    assert ProcessingStatus.PENDING.value == "pending"
    assert ProcessingStatus.COMPLETED.value == "completed"
    assert ProcessingStatus.FAILED.value == "failed"


def test_paper_minimal():
    p = Paper(zotero_key="KEY1", title="Test Paper", authors="Alice; Bob")
    assert p.zotero_key == "KEY1"
    assert p.status == ProcessingStatus.PENDING
    assert p.collections == []
    assert p.tags == []


def test_paper_full(sample_paper):
    p = Paper(**sample_paper)
    assert p.title == "Attention Is All You Need"
    assert "Vaswani" in p.authors
    assert len(p.attachments) == 1


def test_paper_default_empty_fields():
    p = Paper(zotero_key="X", title="T", authors="A")
    assert p.abstract == ""
    assert p.doi == ""
    assert p.analysis is None
    assert p.embeddings is None
