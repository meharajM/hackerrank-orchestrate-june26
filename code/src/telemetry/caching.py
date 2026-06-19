"""
Content-addressed response cache for model calls.
Generates a unique cache key from model_name + prompt + image hashes.
Stores responses as JSON files in a local directory.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ResponseCache:
    """File-system-backed, content-addressed cache for model responses."""

    def __init__(self, cache_dir: Optional[Path] = None, enabled: bool = True):
        self._enabled = enabled
        if cache_dir is None:
            # Default: code/evaluation/.cache/
            self._cache_dir = (
                Path(__file__).resolve().parent.parent.parent / "evaluation" / ".cache"
            )
        else:
            self._cache_dir = Path(cache_dir)
        if self._enabled:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._hits = 0
        self._misses = 0

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    @staticmethod
    def _hash_content(content: str) -> str:
        """SHA-256 hash of a string."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_file(file_path: Path) -> str:
        """SHA-256 hash of a file's contents."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def make_key(
        self,
        model_name: str,
        prompt: str,
        system_prompt: str = "",
        image_paths: Optional[list[Path]] = None,
    ) -> str:
        """Generate a deterministic cache key from call parameters."""
        key_parts = [
            f"model:{model_name}",
            f"system:{system_prompt}",
            f"prompt:{prompt}",
        ]

        if image_paths:
            for img_path in sorted(image_paths, key=str):
                if img_path.exists():
                    key_parts.append(f"img:{self._hash_file(img_path)}")
                else:
                    key_parts.append(f"img_missing:{img_path.name}")

        combined = "\n".join(key_parts)
        return self._hash_content(combined)

    def get(self, cache_key: str) -> Optional[str]:
        """Look up a cached response.  Returns None on miss."""
        if not self._enabled:
            self._misses += 1
            return None

        cache_file = self._cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._hits += 1
                logger.debug(f"Cache HIT: {cache_key[:12]}...")
                return data.get("response", "")
            except Exception as e:
                logger.warning(f"Cache read error for {cache_key}: {e}")
                try:
                    cache_file.unlink(missing_ok=True)
                except Exception:
                    logger.debug("Failed to remove corrupt cache file %s", cache_file)
                self._misses += 1
                return None
        else:
            self._misses += 1
            return None

    def put(self, cache_key: str, response: str) -> None:
        """Store a response in the cache."""
        if not self._enabled:
            return

        cache_file = self._cache_dir / f"{cache_key}.json"
        temp_file = cache_file.with_suffix(f".{os.getpid()}.tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump({"key": cache_key, "response": response}, f)
            os.replace(temp_file, cache_file)
        except Exception as e:
            logger.warning(f"Cache write error for {cache_key}: {e}")
            temp_file.unlink(missing_ok=True)

    def clear(self) -> int:
        """Delete all cached responses.  Returns number of files removed."""
        count = 0
        if self._cache_dir.exists():
            for f in self._cache_dir.glob("*.json"):
                f.unlink()
                count += 1
        self._hits = 0
        self._misses = 0
        return count

    def summary(self) -> dict:
        """Return cache statistics."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_lookups": total,
            "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
            "cache_dir": str(self._cache_dir),
        }
