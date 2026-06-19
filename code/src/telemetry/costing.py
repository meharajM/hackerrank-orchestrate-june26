"""
Token and pricing tracker for model API calls.
Tracks aggregated pricing across a pipeline run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ModelPricing:
    """Pricing multipliers per 1M tokens for a model."""
    model_name: str
    input_cost_per_1m: float   # USD per 1M input tokens
    output_cost_per_1m: float  # USD per 1M output tokens


# ── Pre-configured pricing tables ────────────────────────────────────────────
GEMINI_FLASH_PRICING = ModelPricing(
    model_name="gemini-2.0-flash",
    input_cost_per_1m=0.075,
    output_cost_per_1m=0.30,
)

GEMINI_THINKING_PRICING = ModelPricing(
    model_name="gemini-2.5-flash",
    input_cost_per_1m=0.15,
    output_cost_per_1m=0.60,
)

FREE_PRICING = ModelPricing(
    model_name="free",
    input_cost_per_1m=0.0,
    output_cost_per_1m=0.0,
)

PRICING_TABLE: dict[str, ModelPricing] = {
    "gemini-2.0-flash": GEMINI_FLASH_PRICING,
    "gemini-2.5-flash": GEMINI_THINKING_PRICING,
    "ollama": FREE_PRICING,
    "mock": FREE_PRICING,
}


def get_pricing(model_name: str) -> ModelPricing:
    """Look up pricing for a model by name.  Falls back to free tier."""
    # Check exact match first
    if model_name in PRICING_TABLE:
        return PRICING_TABLE[model_name]
    # Check partial match (e.g. "gemini-2.0-flash" in "Gemini (gemini-2.0-flash)")
    lower = model_name.lower()
    for key, pricing in PRICING_TABLE.items():
        if key in lower:
            return pricing
    return FREE_PRICING


@dataclass
class CostTracker:
    """Tracks token usage and estimated cost across a pipeline run."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_calls: int = 0
    estimated_cost_usd: float = 0.0
    _breakdown: list[dict] = field(default_factory=list)

    def record(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cached: bool = False,
    ) -> float:
        """Record a single call and return its incremental cost in USD."""
        pricing = get_pricing(model_name)

        if cached:
            # Cached calls have zero cost
            cost = 0.0
        else:
            cost = (
                (input_tokens / 1_000_000) * pricing.input_cost_per_1m
                + (output_tokens / 1_000_000) * pricing.output_cost_per_1m
            )

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_calls += 1
        self.estimated_cost_usd += cost

        self._breakdown.append({
            "model": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached": cached,
            "cost_usd": round(cost, 8),
        })

        return cost

    def summary(self) -> dict:
        """Return a summary dict suitable for logging or display."""
        return {
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "breakdown": self._breakdown,
        }
