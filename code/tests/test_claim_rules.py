from src.pipeline.claim_rules import (
    detect_instruction_text,
    extract_claim_signals,
    issue_matches_claim,
    part_matches_claim,
)


def test_extract_claim_signals_prefers_specific_part_language():
    signals = extract_claim_signals(
        "The back of the car has a dent now. Mostly the rear bumper area.",
        "car",
    )

    assert signals.primary_part == "rear_bumper"
    assert signals.issue_hypothesis == "dent"


def test_extract_claim_signals_handles_hinge_and_screen_cases():
    signals = extract_claim_signals(
        "The hinge area has broken and the screen wobbles.",
        "laptop",
    )

    assert signals.primary_part == "hinge"
    assert signals.issue_hypothesis == "broken_part"


def test_detect_instruction_text_ignores_normal_support_language():
    flagged, detail = detect_instruction_text(
        "Please review the headlight damage and let me know if you need another photo."
    )

    assert flagged is False
    assert detail == ""


def test_part_and_issue_matching_are_conservative():
    assert part_matches_claim("rear_bumper", "rear_bumper", "car") is True
    assert part_matches_claim("rear_bumper", "front_bumper", "car") is False
    assert issue_matches_claim("broken_part", "missing_part") is True
    assert issue_matches_claim("scratch", "dent") is False
