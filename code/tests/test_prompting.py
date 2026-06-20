from src import build_claim_processing_context, process_claim_batch
from src.config import get_config
from src.csv_io import read_claims
from src.prompting import FilePromptProvider, resolve_prompt


class RecordingExecutor:
    def __init__(self):
        self.claim_ids: list[str] = []

    def run(self, claims, context, process_one):
        results = []
        for claim in claims:
            self.claim_ids.append(claim.user_id)
            results.append(process_one(claim, context))
        return results


def test_file_prompt_provider_always_includes_core_security():
    provider = FilePromptProvider(get_config().prompts_dir)

    prompt = provider.get_prompt("claim_parser", "fallback")

    assert "Core Security Rules:" in prompt
    assert "You are an expert claims text parser." in prompt


def test_resolve_prompt_can_load_only_needed_shared_sections():
    provider = FilePromptProvider(get_config().prompts_dir)

    prompt = resolve_prompt(
        provider,
        name="image_reviewer",
        fallback="fallback",
        shared_sections=("json_only", "vision_grounding"),
    )

    assert "Vision Grounding:" in prompt
    assert "Output Discipline:" in prompt
    assert "Return one JSON object for this single image review." in prompt


def test_process_claim_batch_accepts_pluggable_executor():
    config = get_config()
    claims = read_claims(config.sample_claims_csv)[:2]
    context = build_claim_processing_context(
        config=config,
        model_name="mock",
        strategy="B",
        cache_enabled=False,
    )
    executor = RecordingExecutor()

    results = process_claim_batch(claims, context, executor=executor)

    assert len(results) == 2
    assert executor.claim_ids == [claim.user_id for claim in claims]
