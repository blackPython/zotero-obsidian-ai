"""
Tests for services/cache.py (with mocked Redis)
"""

import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def redis_cache(mock_config):
    """Create a RedisCache with mocked redis client"""
    with patch("services.cache.redis") as mock_redis_mod:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis_mod.from_url.return_value = mock_client

        from services.cache import RedisCache

        rc = RedisCache(mock_config)
        rc._client = mock_client
        yield rc, mock_client


def test_available(redis_cache):
    rc, mock_client = redis_cache
    assert rc.available is True

    mock_client.ping.side_effect = Exception("down")
    assert rc.available is False


def test_cache_paper(redis_cache, sample_paper):
    rc, mock_client = redis_cache
    assert rc.cache_paper("ABC123", sample_paper) is True
    mock_client.setex.assert_called_once()


def test_get_paper_hit(redis_cache, sample_paper):
    rc, mock_client = redis_cache
    mock_client.get.return_value = json.dumps(sample_paper)
    result = rc.get_paper("ABC123")
    assert result["title"] == "Attention Is All You Need"


def test_get_paper_miss(redis_cache):
    rc, mock_client = redis_cache
    mock_client.get.return_value = None
    assert rc.get_paper("MISSING") is None


def test_cache_analysis(redis_cache):
    rc, mock_client = redis_cache
    analysis = {"main": "good paper", "concepts": "transformers"}
    assert rc.cache_analysis("ABC123", analysis) is True


def test_qa_cache_round_trip(redis_cache):
    rc, mock_client = redis_cache

    # Cache a Q&A
    rc.cache_qa("ABC123", "What is this?", "It's a paper about transformers.")
    assert mock_client.setex.called

    # Get it back
    mock_client.get.return_value = json.dumps({
        "question": "What is this?",
        "answer": "It's a paper about transformers.",
    })
    answer = rc.get_qa("ABC123", "What is this?")
    assert "transformers" in answer


def test_invalidate_paper(redis_cache):
    rc, mock_client = redis_cache
    mock_client.scan_iter.return_value = ["qa:ABC123:abc"]
    rc.invalidate_paper("ABC123")
    mock_client.delete.assert_called_once()


def test_rate_limit(redis_cache):
    rc, mock_client = redis_cache
    mock_client.incr.return_value = 1
    assert rc.check_rate_limit("test-key") is True

    mock_client.incr.return_value = 11
    assert rc.check_rate_limit("test-key", max_requests=10) is False


def test_cache_fails_gracefully(redis_cache, sample_paper):
    rc, mock_client = redis_cache
    mock_client.setex.side_effect = Exception("Redis down")
    # Should return False, not raise
    assert rc.cache_paper("ABC123", sample_paper) is False
