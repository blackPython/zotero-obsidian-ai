"""
Shared test fixtures
"""

import os
import sys
import json
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure backend is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temp data directory structure"""
    (tmp_path / "data" / "cache" / "pdfs").mkdir(parents=True)
    (tmp_path / "data" / "processed").mkdir(parents=True)
    (tmp_path / "data" / "queue").mkdir(parents=True)
    (tmp_path / "config" / "prompts").mkdir(parents=True)
    (tmp_path / "logs").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_prompts_yaml(tmp_data_dir):
    """Write a minimal prompts YAML for tests"""
    import yaml

    prompts = {
        "initial_analysis": {
            "system_prompt": "You are a research assistant.",
            "main_prompt": "Analyze: {title}\n{authors}\n{abstract}\n{full_text}",
        },
        "concept_extraction": {
            "prompt": "Extract concepts: {content}",
        },
        "qa_system": {
            "system_prompt": 'Expert on "{title}".',
            "qa_prompt": 'Paper "{title}". Question: {question}. Context: {context}',
        },
        "summary_types": {
            "one_line": {"prompt": "One-line: {title} - {abstract}"},
            "technical": {"prompt": "Technical: {title} - {abstract}"},
        },
        "literature_connections": {
            "prompt": "Connections: {paper_info}\n{existing_notes}",
        },
        "custom_analysis": {
            "research_gap": {"prompt": "Gaps: {content}"},
            "critique": {"prompt": "Critique: {content}"},
        },
    }
    path = tmp_data_dir / "config" / "prompts" / "paper_analysis.yaml"
    with open(path, "w") as f:
        yaml.dump(prompts, f)
    return path


@pytest.fixture
def mock_config(tmp_data_dir):
    """Create a Config pointing at temp dirs"""
    from utils.config import Config

    cfg = Config.__new__(Config)
    cfg.zotero_api_key = "test-key"
    cfg.zotero_library_id = "12345"
    cfg.zotero_library_type = "user"
    cfg.sync_days_back = 30
    cfg.sync_interval = 300
    cfg.aws_profile = ""
    cfg.aws_region = "us-east-1"
    cfg.bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    cfg.max_tokens = 4096
    cfg.chunk_size = 3000
    cfg.chunk_overlap = 200
    cfg.redis_url = "redis://localhost:6379/0"
    cfg.base_dir = tmp_data_dir
    cfg.data_dir = tmp_data_dir / "data"
    cfg.config_dir = tmp_data_dir / "config"
    cfg.logs_dir = tmp_data_dir / "logs"
    return cfg


@pytest.fixture
def sample_paper():
    """A realistic paper dict"""
    return {
        "zotero_key": "ABC123",
        "title": "Attention Is All You Need",
        "authors": "Ashish Vaswani; Noam Shazeer; Niki Parmar",
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
        "year": "2017",
        "doi": "10.5555/3295222.3295349",
        "url": "https://arxiv.org/abs/1706.03762",
        "tags": ["transformers", "attention"],
        "collections": ["Deep Learning/NLP"],
        "item_type": "conferencePaper",
        "publication": "NeurIPS 2017",
        "volume": "",
        "issue": "",
        "pages": "",
        "extra": "",
        "attachments": [
            {"key": "ATT1", "title": "Full Text", "filename": "paper.pdf", "md5": "abc"}
        ],
        "notes": [],
    }


@pytest.fixture
def test_client():
    """FastAPI TestClient with mocked services"""
    # Patch globals before importing app
    with patch("main.ZoteroMonitor") as MockZM, \
         patch("main.BedrockProcessor") as MockBP, \
         patch("main.RedisCache") as MockRC:

        mock_zm = MagicMock()
        mock_bp = MagicMock()
        mock_cache = MagicMock()
        mock_cache.available = False

        MockZM.return_value = mock_zm
        MockBP.return_value = mock_bp
        MockRC.return_value = mock_cache

        from main import app
        client = TestClient(app)
        yield client, mock_zm, mock_bp, mock_cache
