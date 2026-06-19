"""
Public import surface for the Multi-Modal Evidence Review System.
"""
from .claim_processing import (
    ClaimProcessingContext,
    ClaimProcessingResult,
    build_claim_processing_context,
    build_model_adapter,
    process_claim,
    process_claim_batch,
)
from .history import FileHistoryRepository, HistoryRepository
from .requirements import FileRequirementsRepository, RequirementsRepository

__all__ = [
    "ClaimProcessingContext",
    "ClaimProcessingResult",
    "HistoryRepository",
    "FileHistoryRepository",
    "RequirementsRepository",
    "FileRequirementsRepository",
    "build_claim_processing_context",
    "build_model_adapter",
    "process_claim",
    "process_claim_batch",
]
