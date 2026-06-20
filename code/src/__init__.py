"""
Public import surface for the Multi-Modal Evidence Review System.
"""
from .batch_runner import (
    BatchRunRequest,
    BatchRunResult,
    run_batch,
)
from .claim_processing import (
    ClaimBatchExecutor,
    ClaimProcessingContext,
    ClaimProcessingResult,
    SequentialClaimExecutor,
    build_claim_processing_context,
    build_model_adapter,
    process_claim,
    process_claim_batch,
    resolve_model_name,
)
from .history import FileHistoryRepository, HistoryRepository
from .prompting import FilePromptProvider, PromptProvider
from .requirements import FileRequirementsRepository, RequirementsRepository
from .runtime import RuntimeSettings, build_runtime_settings

__all__ = [
    "BatchRunRequest",
    "BatchRunResult",
    "ClaimBatchExecutor",
    "ClaimProcessingContext",
    "ClaimProcessingResult",
    "HistoryRepository",
    "FileHistoryRepository",
    "PromptProvider",
    "FilePromptProvider",
    "RequirementsRepository",
    "FileRequirementsRepository",
    "RuntimeSettings",
    "SequentialClaimExecutor",
    "build_claim_processing_context",
    "build_runtime_settings",
    "build_model_adapter",
    "process_claim",
    "process_claim_batch",
    "run_batch",
]
