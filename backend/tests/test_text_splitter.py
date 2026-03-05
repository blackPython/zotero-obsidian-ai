"""
Tests for utils/text_splitter.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.text_splitter import TextSplitter


def test_empty_text():
    ts = TextSplitter()
    assert ts.split_text("") == []


def test_short_text_single_chunk():
    ts = TextSplitter(chunk_size=1000)
    text = "This is a short paper."
    chunks = ts.split_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_splits_long_text():
    ts = TextSplitter(chunk_size=100, chunk_overlap=20)
    text = "Hello world. " * 50  # ~650 chars
    chunks = ts.split_text(text)
    assert len(chunks) > 1
    # Verify no chunk exceeds size by too much (sentence boundary may push slightly)
    for chunk in chunks:
        assert len(chunk) <= 150  # generous tolerance


def test_overlap_present():
    ts = TextSplitter(chunk_size=100, chunk_overlap=30)
    text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five. Sentence six. Sentence seven. Sentence eight. Sentence nine. Sentence ten."
    chunks = ts.split_text(text)
    if len(chunks) >= 2:
        # There should be some overlapping content
        end_of_first = chunks[0][-30:]
        assert any(word in chunks[1] for word in end_of_first.split() if len(word) > 3)


def test_clean_text():
    ts = TextSplitter()
    dirty = "Hello\r\n  world\r  \t foo   bar"
    cleaned = ts._clean_text(dirty)
    assert "\r" not in cleaned
    assert "  " not in cleaned  # collapsed whitespace


def test_split_by_sections():
    ts = TextSplitter()
    text = """Abstract
This is the abstract.

Introduction
This is the introduction.

Methods
We used these methods.

Results
Here are results.

Conclusion
In conclusion."""

    sections = ts.split_by_sections(text)
    assert "abstract" in sections
    assert "introduction" in sections
    assert "methods" in sections
    assert "results" in sections
    assert "conclusion" in sections
    assert "abstract" in sections["abstract"].lower() or "This is the abstract" in sections["abstract"]


def test_find_sentence_boundary():
    ts = TextSplitter()
    text = "First sentence. Second sentence. Third"
    boundary = ts._find_sentence_boundary(text)
    assert boundary > 0
    assert text[boundary - 1] == "."
