from pathlib import Path

from src import build_claim_processing_context, process_claim, process_claim_batch
from src.config import get_config
from src.csv_io import read_claims
from src.schemas import EvidenceRequirement, UserHistory
from src.telemetry.events import TelemetryEvent


class StubHistoryRepository:
    def __init__(self, user_history: UserHistory | None):
        self.user_history = user_history
        self.requested_user_ids: list[str] = []

    def get_user_history(self, user_id: str) -> UserHistory | None:
        self.requested_user_ids.append(user_id)
        return self.user_history


class StubRequirementsRepository:
    def __init__(self, requirements: list[EvidenceRequirement]):
        self.requirements = requirements
        self.requests: list[tuple[str, str | None]] = []

    def get_requirements_for_claim(
        self,
        claim_object: str,
        issue_family: str | None = None,
    ) -> list[EvidenceRequirement]:
        self.requests.append((claim_object, issue_family))
        return self.requirements


class StubCacheBackend:
    def __init__(self):
        self._hits = 0
        self._misses = 0
        self.get_calls = 0
        self.put_calls = 0
        self.store: dict[str, str] = {}

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    def make_key(
        self,
        model_name: str,
        prompt: str,
        system_prompt: str = "",
        image_paths: list[Path] | None = None,
    ) -> str:
        path_names = tuple(str(path) for path in image_paths or [])
        return repr((model_name, prompt, system_prompt, path_names))

    def get(self, cache_key: str) -> str | None:
        self.get_calls += 1
        if cache_key in self.store:
            self._hits += 1
            return self.store[cache_key]
        self._misses += 1
        return None

    def put(self, cache_key: str, response: str) -> None:
        self.put_calls += 1
        self.store[cache_key] = response

    def summary(self) -> dict:
        return {"hits": self._hits, "misses": self._misses}


class StubEventSink:
    def __init__(self):
        self.events: list[TelemetryEvent] = []

    def record(self, event: TelemetryEvent) -> None:
        self.events.append(event)

    def summary(self) -> dict:
        return {"total_events": len(self.events)}

    def flush(self, path=None):
        return Path(path or "stub-events.json")


class StubCostRecorder:
    def __init__(self):
        self.records: list[dict] = []

    def record(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cached: bool = False,
    ) -> float:
        self.records.append(
            {
                "model_name": model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cached": cached,
            }
        )
        return 0.0

    def summary(self) -> dict:
        return {"total_calls": len(self.records)}


def test_process_claim_from_public_api():
    """A single claim should be processable via the public import surface."""
    config = get_config()
    claim = read_claims(config.sample_claims_csv)[0]
    context = build_claim_processing_context(
        config=config,
        model_name="mock",
        strategy="B",
        cache_enabled=False,
    )

    result = process_claim(claim, context)

    assert result.output.user_id == claim.user_id
    assert result.output.claim_object == claim.claim_object
    assert result.event is not None
    assert result.event.user_id == claim.user_id
    assert context.event_logger.summary()["total_events"] == 1


def test_process_claim_batch_reuses_shared_context():
    """Multiple claims should be processable through one reusable context."""
    config = get_config()
    claims = read_claims(config.sample_claims_csv)[:2]
    context = build_claim_processing_context(
        config=config,
        model_name="mock",
        strategy="B",
        cache_enabled=False,
    )

    results = process_claim_batch(claims, context)

    assert len(results) == 2
    assert [result.output.user_id for result in results] == [claim.user_id for claim in claims]
    assert context.event_logger.summary()["total_events"] == 2


def test_process_claim_accepts_injected_repositories():
    """The application service should depend on repository interfaces, not file-bound managers."""
    config = get_config()
    claim = read_claims(config.sample_claims_csv)[0]
    history = UserHistory(
        user_id=claim.user_id,
        past_claim_count=7,
        accept_claim=2,
        manual_review_claim=3,
        rejected_claim=2,
        last_90_days_claim_count=4,
        history_flags="user_history_risk",
        history_summary="Escalate due to repeated prior claims.",
    )
    requirements = [
        EvidenceRequirement(
            requirement_id="REQ_CUSTOM",
            claim_object=claim.claim_object,
            applies_to="all",
            minimum_image_evidence="One clear evidence image.",
        )
    ]
    history_repository = StubHistoryRepository(history)
    requirements_repository = StubRequirementsRepository(requirements)

    context = build_claim_processing_context(
        config=config,
        model_name="mock",
        strategy="B",
        cache_enabled=False,
        history_repository=history_repository,
        requirements_repository=requirements_repository,
    )

    result = process_claim(claim, context)

    assert history_repository.requested_user_ids == [claim.user_id]
    assert requirements_repository.requests == [(claim.claim_object, None)]
    assert result.user_history == history
    assert result.evidence_requirements == requirements


def test_process_claim_accepts_injected_cache_and_telemetry_providers():
    """The application service should honor injected cache and telemetry implementations."""
    config = get_config()
    claim = read_claims(config.sample_claims_csv)[0]
    cache = StubCacheBackend()
    event_sink = StubEventSink()
    cost_recorder = StubCostRecorder()

    context = build_claim_processing_context(
        config=config,
        model_name="mock",
        strategy="B",
        cache_enabled=True,
        cache=cache,
        event_logger=event_sink,
        cost_tracker=cost_recorder,
    )

    result = process_claim(claim, context)

    assert result.event is not None
    assert event_sink.events and event_sink.events[0].user_id == claim.user_id
    assert cache.get_calls > 0
    assert cache.put_calls > 0
    assert cost_recorder.records
