"""
Configuration management for the backend service
"""

import os
from pathlib import Path
from dataclasses import dataclass, field


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    return int(os.getenv(key, str(default)))


@dataclass
class Config:
    """Application configuration"""

    # Zotero settings
    zotero_api_key: str = field(default_factory=lambda: _env("ZOTERO_API_KEY"))
    zotero_library_id: str = field(default_factory=lambda: _env("ZOTERO_LIBRARY_ID"))
    zotero_library_type: str = field(default_factory=lambda: _env("ZOTERO_LIBRARY_TYPE", "user"))
    sync_days_back: int = field(default_factory=lambda: _env_int("SYNC_DAYS_BACK", 30))
    sync_interval: int = field(default_factory=lambda: _env_int("SYNC_INTERVAL", 300))

    # Redis
    redis_url: str = field(default_factory=lambda: _env("REDIS_URL", "redis://localhost:6379/0"))

    # AWS Bedrock settings
    aws_region: str = field(default_factory=lambda: _env("AWS_REGION", "us-east-1"))
    bedrock_model_id: str = field(default_factory=lambda: _env("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"))
    max_tokens: int = field(default_factory=lambda: _env_int("MAX_TOKENS", 4096))
    chunk_size: int = field(default_factory=lambda: _env_int("CHUNK_SIZE", 3000))
    chunk_overlap: int = field(default_factory=lambda: _env_int("CHUNK_OVERLAP", 200))

    # Directory paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    data_dir: Path = field(default=None)
    config_dir: Path = field(default=None)
    logs_dir: Path = field(default=None)

    def __post_init__(self):
        """Ensure directories exist"""
        if self.data_dir is None:
            self.data_dir = self.base_dir / "data"
        if self.config_dir is None:
            self.config_dir = self.base_dir / "config"
        if self.logs_dir is None:
            self.logs_dir = self.base_dir / "logs"

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.data_dir / "cache" / "pdfs").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "processed").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "queue").mkdir(parents=True, exist_ok=True)
