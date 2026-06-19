"""
Evaluation package exports.
"""
from .metrics import evaluate_predictions
from .reporting import build_markdown_report, generate_slice_metrics

__all__ = [
    "evaluate_predictions",
    "build_markdown_report",
    "generate_slice_metrics",
]
