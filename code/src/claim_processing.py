"""
Importable application service for processing claims.
Provides single-claim and batch APIs that can be reused by CLI entrypoints,
future web services, and external library consumers.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Sequence

from .config import Config, get_config
from .history import FileHistoryRepository, HistoryRepository
from .models import GeminiAdapter, MockAdapter, OllamaAdapter
from .models.base import ModelAdapter
from .pipeline.strategy_escalation import run_escalation_pipeline
from .pipeline.strategy_single_pass import run_single_pass_pipeline
from .pipeline.strategy_staged import run_staged_pipeline
from .requirements import FileRequirementsRepository, RequirementsRepository
from .schemas import ClaimInput, ClaimOutput, EvidenceRequirement, UserHistory
from .telemetry.caching import ResponseCache
from .telemetry.costing import CostTracker
from .telemetry.events import EventLogger, TelemetryEvent

StrategyName = Literal["A", "B", "C"]
ModelName = Literal["gemini", "ollama", "mock"]


@dataclass
class ClaimProcessingContext:
    """Dependencies and runtime configuration for claim processing."""

    dataset_dir: Path
    model: ModelAdapter
    history_repository: HistoryRepository
    requirements_repository: RequirementsRepository
    strategy: StrategyName = "B"
    escalation_model: Optional[ModelAdapter] = None
    cache: Optional[ResponseCache] = None
    event_logger: Optional[EventLogger] = None
    cost_tracker: Optional[CostTracker] = None


@dataclass
class ClaimProcessingResult:
    """Result of processing a single claim."""

    output: ClaimOutput
    user_history: Optional[UserHistory]
    evidence_requirements: list[EvidenceRequirement]
    event: Optional[TelemetryEvent] = None


def build_model_adapter(
    model_name: ModelName,
    config: Optional[Config] = None,
    *,
    allow_fallback: bool = True,
) -> ModelAdapter:
    """Build a model adapter from a simple model name."""
    config = config or get_config()

    if model_name == "gemini":
        if config.has_gemini:
            return GeminiAdapter(model_name=config.gemini_model)
        if allow_fallback:
            return MockAdapter()
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

    if model_name == "ollama":
        return OllamaAdapter(model_name=config.ollama_model, base_url=config.ollama_base_url)

    return MockAdapter()


def build_claim_processing_context(
    *,
    config: Optional[Config] = None,
    model_name: ModelName = "mock",
    strategy: StrategyName = "B",
    cache_enabled: bool = True,
    cache_dir: Optional[Path] = None,
    allow_model_fallback: bool = True,
    history_repository: Optional[HistoryRepository] = None,
    requirements_repository: Optional[RequirementsRepository] = None,
) -> ClaimProcessingContext:
    """Build a reusable processing context for CLI, batch, or service usage."""
    config = config or get_config()

    history_repository = history_repository or FileHistoryRepository(config.user_history_csv)
    requirements_repository = requirements_repository or FileRequirementsRepository(
        config.evidence_requirements_csv
    )
    cache = ResponseCache(cache_dir=cache_dir, enabled=cache_enabled)
    event_logger = EventLogger()
    cost_tracker = CostTracker()

    model = build_model_adapter(model_name, config, allow_fallback=allow_model_fallback)
    model.wire_cache(cache)

    escalation_model: Optional[ModelAdapter] = None
    if strategy == "C":
        if config.has_gemini:
            escalation_model = build_model_adapter("gemini", config, allow_fallback=False)
            escalation_model.wire_cache(cache)
        else:
            escalation_model = model

    return ClaimProcessingContext(
        dataset_dir=config.dataset_dir,
        model=model,
        history_repository=history_repository,
        requirements_repository=requirements_repository,
        strategy=strategy,
        escalation_model=escalation_model,
        cache=cache,
        event_logger=event_logger,
        cost_tracker=cost_tracker,
    )


def process_claim(claim: ClaimInput, context: ClaimProcessingContext) -> ClaimProcessingResult:
    """Process a single claim through the configured strategy and dependencies."""
    timer_start = time.monotonic()
    stats_before = context.model.get_stats()
    has_distinct_escalation_model = (
        context.strategy == "C"
        and context.escalation_model is not None
        and context.escalation_model is not context.model
    )
    esc_before = (
        context.escalation_model.get_stats()
        if has_distinct_escalation_model
        else {"call_count": 0, "total_input_tokens": 0, "total_output_tokens": 0}
    )
    cache_hits_before = context.cache.hits if context.cache else 0
    cache_misses_before = context.cache.misses if context.cache else 0

    user_history = context.history_repository.get_user_history(claim.user_id)
    evidence_requirements = context.requirements_repository.get_requirements_for_claim(claim.claim_object)

    output = _run_strategy(
        claim=claim,
        context=context,
        user_history=user_history,
        evidence_requirements=evidence_requirements,
    )

    event = _record_processing_metrics(
        claim=claim,
        output=output,
        context=context,
        timer_start=timer_start,
        stats_before=stats_before,
        esc_before=esc_before,
        has_distinct_escalation_model=has_distinct_escalation_model,
        cache_hits_before=cache_hits_before,
        cache_misses_before=cache_misses_before,
    )

    return ClaimProcessingResult(
        output=output,
        user_history=user_history,
        evidence_requirements=evidence_requirements,
        event=event,
    )


def process_claim_batch(
    claims: Sequence[ClaimInput],
    context: ClaimProcessingContext,
) -> list[ClaimProcessingResult]:
    """Process multiple claims using a shared reusable context."""
    return [process_claim(claim, context) for claim in claims]


def _run_strategy(
    *,
    claim: ClaimInput,
    context: ClaimProcessingContext,
    user_history: Optional[UserHistory],
    evidence_requirements: list[EvidenceRequirement],
) -> ClaimOutput:
    """Dispatch a claim into the configured pipeline strategy."""
    if context.strategy == "A":
        return run_single_pass_pipeline(
            claim=claim,
            model=context.model,
            dataset_dir=context.dataset_dir,
            user_history=user_history,
            evidence_requirements=evidence_requirements,
        )

    if context.strategy == "C":
        escalation_model = context.escalation_model or context.model
        return run_escalation_pipeline(
            claim=claim,
            model=context.model,
            escalation_model=escalation_model,
            dataset_dir=context.dataset_dir,
            user_history=user_history,
            evidence_requirements=evidence_requirements,
        )

    return run_staged_pipeline(
        claim=claim,
        model=context.model,
        dataset_dir=context.dataset_dir,
        user_history=user_history,
        evidence_requirements=evidence_requirements,
    )


def _stats_delta(after: dict, before: dict) -> dict:
    """Compute a non-negative delta between adapter stats snapshots."""
    keys = {"call_count", "total_input_tokens", "total_output_tokens"}
    return {
        key: max(0, int(after.get(key, 0) or 0) - int(before.get(key, 0) or 0))
        for key in keys
    }


def _record_processing_metrics(
    *,
    claim: ClaimInput,
    output: ClaimOutput,
    context: ClaimProcessingContext,
    timer_start: float,
    stats_before: dict,
    esc_before: dict,
    has_distinct_escalation_model: bool,
    cache_hits_before: int,
    cache_misses_before: int,
) -> Optional[TelemetryEvent]:
    """Record per-claim telemetry and cost accounting."""
    latency = round(time.monotonic() - timer_start, 4)
    model_delta = _stats_delta(context.model.get_stats(), stats_before)
    row_input_tokens = model_delta["total_input_tokens"]
    row_output_tokens = model_delta["total_output_tokens"]
    row_call_count = model_delta["call_count"]

    esc_delta = {"call_count": 0, "total_input_tokens": 0, "total_output_tokens": 0}
    if has_distinct_escalation_model and context.escalation_model is not None:
        esc_delta = _stats_delta(context.escalation_model.get_stats(), esc_before)
        row_input_tokens += esc_delta["total_input_tokens"]
        row_output_tokens += esc_delta["total_output_tokens"]
        row_call_count += esc_delta["call_count"]

    cache_hits_after = context.cache.hits if context.cache else cache_hits_before
    cache_misses_after = context.cache.misses if context.cache else cache_misses_before
    cache_hit_delta = max(0, cache_hits_after - cache_hits_before)
    cache_miss_delta = max(0, cache_misses_after - cache_misses_before)
    row_fully_cached = row_call_count == 0 and cache_hit_delta > 0
    escalated = "[Escalated:" in getattr(output, "claim_status_justification", "")

    event: Optional[TelemetryEvent] = None
    if context.event_logger is not None:
        event = TelemetryEvent(
            user_id=claim.user_id,
            model=context.model.name,
            stage=f"strategy_{context.strategy}",
            latency_seconds=latency,
            input_tokens=row_input_tokens,
            output_tokens=row_output_tokens,
            cached=row_fully_cached,
            escalated=escalated,
        )
        context.event_logger.record(event)

    if context.cost_tracker is not None:
        context.cost_tracker.record(
            context.model.name,
            model_delta["total_input_tokens"],
            model_delta["total_output_tokens"],
            cached=(model_delta["call_count"] == 0 and cache_hit_delta > 0),
        )
        if has_distinct_escalation_model and context.escalation_model is not None and escalated:
            context.cost_tracker.record(
                context.escalation_model.name,
                esc_delta["total_input_tokens"],
                esc_delta["total_output_tokens"],
                cached=(esc_delta["call_count"] == 0 and cache_hit_delta > 0 and cache_miss_delta == 0),
            )

    return event


__all__ = [
    "ClaimProcessingContext",
    "ClaimProcessingResult",
    "ModelName",
    "StrategyName",
    "build_claim_processing_context",
    "build_model_adapter",
    "process_claim",
    "process_claim_batch",
]
