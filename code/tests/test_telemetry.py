"""
Tests for the telemetry package: costing, events, and caching.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import importlib.util

import pytest

from src import claim_processing as claim_processing_module
from src.telemetry.costing import CostTracker, get_pricing, FREE_PRICING, GEMINI_FLASH_PRICING
from src.telemetry.events import EventLogger, TelemetryEvent
from src.telemetry.caching import ResponseCache

_MAIN_PATH = Path(__file__).resolve().parent.parent / "main.py"
_MAIN_SPEC = importlib.util.spec_from_file_location("repo_main", _MAIN_PATH)
repo_main = importlib.util.module_from_spec(_MAIN_SPEC)
assert _MAIN_SPEC.loader is not None
_MAIN_SPEC.loader.exec_module(repo_main)


# ── CostTracker tests ────────────────────────────────────────────────────


class TestCostTracker:
    def test_record_gemini_cost(self):
        tracker = CostTracker()
        cost = tracker.record("gemini-2.0-flash", input_tokens=1000, output_tokens=500)
        # input: 1000/1M * 0.075 = 0.000075
        # output: 500/1M * 0.30 = 0.00015
        assert abs(cost - 0.000225) < 1e-8
        assert tracker.total_calls == 1
        assert tracker.total_input_tokens == 1000
        assert tracker.total_output_tokens == 500

    def test_record_free_model(self):
        tracker = CostTracker()
        cost = tracker.record("mock", input_tokens=5000, output_tokens=2000)
        assert cost == 0.0
        assert tracker.total_calls == 1

    def test_record_cached_is_free(self):
        tracker = CostTracker()
        cost = tracker.record("gemini-2.0-flash", input_tokens=1000, output_tokens=500, cached=True)
        assert cost == 0.0
        assert tracker.total_calls == 1
        # Tokens still counted for tracking purposes
        assert tracker.total_input_tokens == 1000

    def test_aggregate_multiple_calls(self):
        tracker = CostTracker()
        tracker.record("gemini-2.0-flash", 1000, 500)
        tracker.record("gemini-2.0-flash", 2000, 1000)
        tracker.record("mock", 3000, 1500)
        assert tracker.total_calls == 3
        assert tracker.total_input_tokens == 6000
        assert tracker.total_output_tokens == 3000
        # Only gemini calls have cost
        expected_cost = (1000 + 2000) / 1e6 * 0.075 + (500 + 1000) / 1e6 * 0.30
        assert abs(tracker.estimated_cost_usd - expected_cost) < 1e-8

    def test_summary_format(self):
        tracker = CostTracker()
        tracker.record("mock", 100, 50)
        s = tracker.summary()
        assert "total_calls" in s
        assert "estimated_cost_usd" in s
        assert "breakdown" in s
        assert len(s["breakdown"]) == 1

    def test_get_pricing_partial_match(self):
        pricing = get_pricing("Gemini (gemini-2.0-flash)")
        assert pricing == GEMINI_FLASH_PRICING

    def test_get_pricing_unknown_fallback(self):
        pricing = get_pricing("some-unknown-model")
        assert pricing == FREE_PRICING


# ── EventLogger tests ────────────────────────────────────────────────────


class TestEventLogger:
    def test_record_and_summary(self):
        logger = EventLogger()
        logger.record(TelemetryEvent(user_id="u1", model="mock", stage="test", latency_seconds=1.5))
        logger.record(TelemetryEvent(user_id="u2", model="mock", stage="test", latency_seconds=2.5, cached=True))
        s = logger.summary()
        assert s["total_events"] == 2
        assert abs(s["total_latency_seconds"] - 4.0) < 1e-4
        assert s["cached_calls"] == 1

    def test_flush_to_file(self, tmp_path):
        logger = EventLogger()
        logger.record(TelemetryEvent(user_id="u1", model="mock", stage="test"))
        out = logger.flush(tmp_path / "test_log.json")
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["total_events"] == 1
        assert len(data["events"]) == 1
        assert data["events"][0]["user_id"] == "u1"

    def test_timer(self):
        import time
        logger = EventLogger()
        t0 = logger.start_timer()
        time.sleep(0.05)
        elapsed = logger.elapsed(t0)
        assert elapsed >= 0.04  # At least 40ms
        assert elapsed < 1.0    # Less than a second

    def test_stats_delta_uses_incremental_values(self):
        before = {"call_count": 2, "total_input_tokens": 100, "total_output_tokens": 40}
        after = {"call_count": 5, "total_input_tokens": 260, "total_output_tokens": 120}
        delta = claim_processing_module._stats_delta(after, before)
        assert delta == {
            "call_count": 3,
            "total_input_tokens": 160,
            "total_output_tokens": 80,
        }


# ── ResponseCache tests ──────────────────────────────────────────────────


class TestResponseCache:
    def test_miss_then_hit(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache")
        key = cache.make_key("mock", "hello world", "")
        assert cache.get(key) is None
        assert cache.misses == 1

        cache.put(key, '{"result": "ok"}')
        result = cache.get(key)
        assert result == '{"result": "ok"}'
        assert cache.hits == 1

    def test_disabled_cache(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache", enabled=False)
        key = cache.make_key("mock", "hello", "")
        cache.put(key, "response")  # no-op when disabled
        assert cache.get(key) is None  # Always miss when disabled
        assert cache.hits == 0
        assert cache.misses == 1  # only the get() call increments miss

    def test_different_prompts_different_keys(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache")
        k1 = cache.make_key("mock", "prompt A", "")
        k2 = cache.make_key("mock", "prompt B", "")
        assert k1 != k2

    def test_same_prompt_same_key(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache")
        k1 = cache.make_key("mock", "same prompt", "sys")
        k2 = cache.make_key("mock", "same prompt", "sys")
        assert k1 == k2

    def test_different_models_different_keys(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache")
        k1 = cache.make_key("gemini", "prompt", "")
        k2 = cache.make_key("ollama", "prompt", "")
        assert k1 != k2

    def test_clear(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache")
        key = cache.make_key("mock", "test", "")
        cache.put(key, "data")
        assert cache.get(key) is not None
        removed = cache.clear()
        assert removed == 1
        assert cache.get(key) is None

    def test_image_hash_in_key(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache")
        # Create a dummy image file
        img = tmp_path / "test_image.jpg"
        img.write_bytes(b"\xff\xd8\xff fake jpeg data")

        k1 = cache.make_key("mock", "prompt", "", image_paths=[img])
        k2 = cache.make_key("mock", "prompt", "", image_paths=None)
        assert k1 != k2

    def test_summary(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache")
        key = cache.make_key("mock", "test", "")
        cache.get(key)  # miss
        cache.put(key, "data")
        cache.get(key)  # hit
        s = cache.summary()
        assert s["hits"] == 1
        assert s["misses"] == 1
        assert s["hit_rate"] == 0.5

    def test_corrupt_cache_file_is_removed_and_treated_as_miss(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache")
        key = cache.make_key("mock", "test", "")
        cache_file = cache.cache_dir / f"{key}.json"
        cache_file.write_text("{not-json", encoding="utf-8")

        assert cache.get(key) is None
        assert not cache_file.exists()


# ── Integration: ModelAdapter cache wiring ───────────────────────────────


class TestModelAdapterCacheWiring:
    def test_cached_text_call(self, tmp_path):
        from src.models.mock_adapter import MockAdapter
        cache = ResponseCache(cache_dir=tmp_path / "cache")
        adapter = MockAdapter()
        adapter.wire_cache(cache)

        # First call: cache miss
        result1, cached1 = adapter.cached_text_call("test prompt")
        assert not cached1
        assert cache.misses == 1

        # Second call: cache hit
        result2, cached2 = adapter.cached_text_call("test prompt")
        assert cached2
        assert cache.hits == 1
        assert result1 == result2

    def test_cached_multimodal_call(self, tmp_path):
        from src.models.mock_adapter import MockAdapter
        cache = ResponseCache(cache_dir=tmp_path / "cache")
        adapter = MockAdapter()
        adapter.wire_cache(cache)

        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8 fake")

        result1, cached1 = adapter.cached_multimodal_call("prompt", [img])
        assert not cached1

        result2, cached2 = adapter.cached_multimodal_call("prompt", [img])
        assert cached2
        assert result1 == result2
