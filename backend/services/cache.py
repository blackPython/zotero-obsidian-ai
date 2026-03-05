"""
Redis caching service for paper data and analysis results
"""

import json
from typing import Any, Dict, Optional
from datetime import timedelta

import redis
from loguru import logger

from utils.config import Config


class RedisCache:
    """Redis-backed cache for paper data and analysis results"""

    def __init__(self, config: Config):
        self.config = config
        self.redis_url = config.redis_url
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            try:
                self._client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                )
                self._client.ping()
                logger.info(f"Connected to Redis at {self.redis_url}")
            except redis.ConnectionError:
                logger.warning("Redis unavailable — caching disabled")
                self._client = None
                raise
        return self._client

    @property
    def available(self) -> bool:
        try:
            self.client.ping()
            return True
        except Exception:
            return False

    # ── Key helpers ────────────────────────────────────────────────
    @staticmethod
    def _paper_key(zotero_key: str) -> str:
        return f"paper:{zotero_key}"

    @staticmethod
    def _analysis_key(zotero_key: str) -> str:
        return f"analysis:{zotero_key}"

    @staticmethod
    def _qa_key(zotero_key: str, question_hash: str) -> str:
        return f"qa:{zotero_key}:{question_hash}"

    # ── Paper cache ───────────────────────────────────────────────
    def cache_paper(self, zotero_key: str, paper_data: Dict, ttl_hours: int = 24) -> bool:
        try:
            self.client.setex(
                self._paper_key(zotero_key),
                timedelta(hours=ttl_hours),
                json.dumps(paper_data, default=str),
            )
            return True
        except Exception as e:
            logger.debug(f"Cache write failed for paper {zotero_key}: {e}")
            return False

    def get_paper(self, zotero_key: str) -> Optional[Dict]:
        try:
            data = self.client.get(self._paper_key(zotero_key))
            return json.loads(data) if data else None
        except Exception:
            return None

    # ── Analysis cache ────────────────────────────────────────────
    def cache_analysis(self, zotero_key: str, analysis: Dict, ttl_hours: int = 168) -> bool:
        """Cache analysis results (default 7 days)"""
        try:
            self.client.setex(
                self._analysis_key(zotero_key),
                timedelta(hours=ttl_hours),
                json.dumps(analysis, default=str),
            )
            return True
        except Exception as e:
            logger.debug(f"Cache write failed for analysis {zotero_key}: {e}")
            return False

    def get_analysis(self, zotero_key: str) -> Optional[Dict]:
        try:
            data = self.client.get(self._analysis_key(zotero_key))
            return json.loads(data) if data else None
        except Exception:
            return None

    # ── Q&A cache ─────────────────────────────────────────────────
    def cache_qa(self, zotero_key: str, question: str, answer: str, ttl_hours: int = 72) -> bool:
        """Cache Q&A responses (default 3 days)"""
        import hashlib
        q_hash = hashlib.md5(question.encode()).hexdigest()[:12]
        try:
            self.client.setex(
                self._qa_key(zotero_key, q_hash),
                timedelta(hours=ttl_hours),
                json.dumps({"question": question, "answer": answer}),
            )
            return True
        except Exception:
            return False

    def get_qa(self, zotero_key: str, question: str) -> Optional[str]:
        import hashlib
        q_hash = hashlib.md5(question.encode()).hexdigest()[:12]
        try:
            data = self.client.get(self._qa_key(zotero_key, q_hash))
            if data:
                return json.loads(data).get("answer")
        except Exception:
            pass
        return None

    # ── Invalidation ──────────────────────────────────────────────
    def invalidate_paper(self, zotero_key: str) -> None:
        """Remove all cached data for a paper"""
        try:
            keys = [self._paper_key(zotero_key), self._analysis_key(zotero_key)]
            # Also remove any Q&A keys
            qa_pattern = f"qa:{zotero_key}:*"
            qa_keys = list(self.client.scan_iter(match=qa_pattern))
            keys.extend(qa_keys)
            if keys:
                self.client.delete(*keys)
        except Exception as e:
            logger.debug(f"Cache invalidation failed for {zotero_key}: {e}")

    # ── Rate limiting ─────────────────────────────────────────────
    def check_rate_limit(self, key: str, max_requests: int = 10, window_seconds: int = 60) -> bool:
        """Simple sliding-window rate limiter. Returns True if allowed."""
        try:
            current = self.client.incr(f"ratelimit:{key}")
            if current == 1:
                self.client.expire(f"ratelimit:{key}", window_seconds)
            return current <= max_requests
        except Exception:
            return True  # fail open
