"""
Tests for API endpoints using mocked services
"""

import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app_client(sample_paper):
    """Create a test client with fully mocked services"""
    import main as main_module

    # Mock all services
    mock_zm = MagicMock()
    mock_zm.fetch_collections.return_value = {"COL1": {"name": "ML", "path": "ML"}}
    mock_zm.fetch_new_items.return_value = [sample_paper]
    mock_zm.get_paper_by_key.return_value = sample_paper
    mock_zm.processed_items = set()

    mock_bp = MagicMock()
    mock_bp.answer_question = AsyncMock(return_value="The paper proposes the transformer architecture.")
    mock_bp.custom_analysis = AsyncMock(return_value="There are gaps in X.")
    mock_bp._load_prompts.return_value = {}

    # Assign to module globals
    main_module.zotero_monitor = mock_zm
    main_module.bedrock_processor = mock_bp
    main_module.cache = None  # no Redis in tests

    from main import app

    client = TestClient(app, raise_server_exceptions=False)
    yield client, mock_zm, mock_bp


def test_health_check(app_client):
    client, _, _ = app_client
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert "timestamp" in data


def test_get_paper(app_client, sample_paper):
    client, mock_zm, _ = app_client
    resp = client.get(f"/api/paper/{sample_paper['zotero_key']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["paper"]["title"] == "Attention Is All You Need"


def test_get_paper_not_found(app_client):
    client, mock_zm, _ = app_client
    mock_zm.get_paper_by_key.return_value = None
    resp = client.get("/api/paper/NONEXISTENT")
    assert resp.status_code == 404


def test_qa_endpoint(app_client, sample_paper):
    client, _, mock_bp = app_client
    resp = client.post("/api/qa", json={
        "zotero_key": sample_paper["zotero_key"],
        "question": "What is the main contribution?",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "transformer" in data["answer"].lower()


def test_custom_analysis(app_client, sample_paper):
    client, _, mock_bp = app_client
    resp = client.post("/api/custom-analysis", json={
        "zotero_key": sample_paper["zotero_key"],
        "analysis_type": "research_gap",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_custom_analysis_unknown_type(app_client, sample_paper):
    client, _, mock_bp = app_client
    mock_bp.custom_analysis = AsyncMock(side_effect=ValueError("Unknown analysis type: foo"))
    resp = client.post("/api/custom-analysis", json={
        "zotero_key": sample_paper["zotero_key"],
        "analysis_type": "foo",
    })
    assert resp.status_code == 400


def test_sync_endpoint(app_client):
    client, mock_zm, _ = app_client
    with patch("services.zotero_monitor.ZoteroMonitor", return_value=mock_zm):
        resp = client.post("/api/sync", json={
            "library_id": "12345",
            "api_key": "test-key",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["count"] >= 0


def test_collections_endpoint(app_client):
    client, _, _ = app_client
    resp = client.get("/api/collections")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "collections" in data


def test_get_prompts(app_client, sample_prompts_yaml):
    client, _, _ = app_client
    # This depends on the config pointing to our test prompts
    # Just verify the endpoint responds
    resp = client.get("/api/prompts")
    # May return empty prompts since config points elsewhere, but should not 500
    assert resp.status_code == 200
