"""
Tests for utils/config.py
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import Config


def test_default_config():
    """Config has sensible defaults"""
    cfg = Config()
    assert cfg.zotero_library_type == "user"
    assert cfg.aws_region == "us-east-1"
    assert cfg.max_tokens == 4096
    assert cfg.chunk_size == 3000
    assert cfg.chunk_overlap == 200
    assert cfg.sync_days_back == 30
    assert cfg.sync_interval == 300
    assert "redis" in cfg.redis_url


def test_config_from_env():
    """Config reads from environment"""
    env = {
        "ZOTERO_API_KEY": "my-key",
        "ZOTERO_LIBRARY_ID": "999",
        "AWS_REGION": "eu-west-1",
        "MAX_TOKENS": "8192",
        "REDIS_URL": "redis://myhost:6380/1",
    }
    with patch.dict(os.environ, env, clear=False):
        cfg = Config()
        assert cfg.zotero_api_key == "my-key"
        assert cfg.zotero_library_id == "999"
        assert cfg.aws_region == "eu-west-1"
        assert cfg.max_tokens == 8192
        assert cfg.redis_url == "redis://myhost:6380/1"


def test_config_creates_directories(tmp_path):
    """Config.__post_init__ creates required directories"""
    cfg = Config.__new__(Config)
    cfg.data_dir = tmp_path / "data"
    cfg.config_dir = tmp_path / "config"
    cfg.logs_dir = tmp_path / "logs"
    cfg.__post_init__()

    assert (tmp_path / "data" / "cache" / "pdfs").exists()
    assert (tmp_path / "data" / "processed").exists()
    assert (tmp_path / "data" / "queue").exists()
