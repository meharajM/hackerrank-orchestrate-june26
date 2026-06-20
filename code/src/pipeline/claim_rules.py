"""
Deterministic claim and evidence normalization rules.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..schemas import ClaimObject, IssueType, normalize_object_part
from ..utils.text import is_multilingual_claim


INJECTION_PATTERNS = [
    r"\bapprove\b",
    r"\bmark (?:this |it )?as valid\b",
    r"\bignore (?:the )?(?:image|review|checks|rules)\b",
    r"\bset (?:valid_image|claim_status|risk_flags)\b",
    r"\bmanual[_ ]review\s*=\s*false\b",
    r"\breturn json\b",
]

PART_KEYWORDS: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    ClaimObject.CAR.value: [
        ("rear_bumper", ("rear bumper", "back bumper", "rear side", "back side", "rear end", "back of the car")),
        ("front_bumper", ("front bumper", "front side", "front-end", "front end", "nose")),
        ("windshield", ("windshield", "windscreen", "front glass", "front windshield", "glass")),
        ("side_mirror", ("side mirror", "mirror")),
        ("headlight", ("headlight", "front light", "lamp")),
        ("taillight", ("tail light", "taillight", "rear light")),
        ("hood", ("hood", "bonnet", "top panel")),
        ("door", ("door", "door panel")),
        ("quarter_panel", ("quarter panel",)),
        ("fender", ("fender",)),
        ("body", ("body", "panel", "side of the car", "car side")),
    ],
    ClaimObject.LAPTOP.value: [
        ("trackpad", ("trackpad", "touchpad")),
        ("keyboard", ("keyboard", "keys", "key area")),
        ("screen", ("screen", "display", "display glass", "monitor")),
        ("hinge", ("hinge", "hinge area")),
        ("lid", ("lid", "top cover", "cover")),
        ("corner", ("corner", "edge", "side corner")),
        ("port", ("port", "charging port", "usb port")),
        ("base", ("base", "bottom")),
        ("body", ("body", "casing", "frame")),
    ],
    ClaimObject.PACKAGE.value: [
        ("package_corner", ("package corner", "box corner", "corner")),
        ("package_side", ("package side", "side wall", "side panel", "outside", "outer side")),
        ("seal", ("seal", "tape", "sealed side", "seal side", "opened side", "flap")),
        ("label", ("label", "shipping label")),
        ("contents", ("contents", "inside", "inner item", "inside item", "inside the package", "inside the box", "product inside")),
        ("item", ("item", "product")),
        ("box", ("box", "package", "parcel")),
    ],
}

ISSUE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("glass_shatter", ("shattered", "shatter", "spider-web crack")),
    ("broken_part", ("broken", "snapped", "detached", "hanging", "loose", "wobble", "wobbles", "not sitting", "misaligned")),
    ("missing_part", ("missing", "gone", "fell off")),
    ("crushed_packaging", ("crushed", "crumpled", "caved in", "collapsed", "smashed")),
    ("torn_packaging", ("torn", "ripped", "opened", "open hua", "phati", "phata", "khola gaya")),
    ("water_damage", ("water damage", "wet", "soaked", "damp", "water stained", "water damaged")),
    ("stain", ("stain", "sticky", "spilled", "spill", "marks from water")),
    ("scratch", ("scratch", "scrape", "scraped", "scuff", "mark")),
    ("dent", ("dent", "dented", "ding")),
    ("crack", ("crack", "cracked", "fracture", "split", "tuta", "tute")),
]

ISSUE_COMPATIBILITY: dict[str, set[str]] = {
    "dent": {"dent"},
    "scratch": {"scratch"},
    "crack": {"crack", "glass_shatter"},
    "glass_shatter": {"glass_shatter", "crack"},
    "broken_part": {"broken_part", "missing_part"},
    "missing_part": {"missing_part", "broken_part"},
    "torn_packaging": {"torn_packaging"},
    "crushed_packaging": {"crushed_packaging"},
    "water_damage": {"water_damage", "stain"},
    "stain": {"stain", "water_damage"},
    "none": {"none"},
    "unknown": {"unknown"},
}

BODY_LIKE_PARTS: dict[str, set[str]] = {
    ClaimObject.CAR.value: {"body", "front_bumper", "rear_bumper", "door", "hood", "fender", "quarter_panel"},
    ClaimObject.LAPTOP.value: {"body", "base", "lid", "corner"},
    ClaimObject.PACKAGE.value: {"box", "package_corner", "package_side"},
}

VALID_ISSUES = {issue.value for issue in IssueType}


@dataclass(frozen=True)
class ClaimSignals:
    primary_part: str
    issue_hypothesis: str
    secondary_targets: list[str]
    has_instruction_text: bool
    instruction_text_detail: str
    language_notes: str
    confidence: float


def detect_instruction_text(text: str) -> tuple[bool, str]:
    """Detect explicit prompt-injection style instructions in user text."""
    lower = text.lower()
    matches = [pattern for pattern in INJECTION_PATTERNS if re.search(pattern, lower)]
    if not matches:
        return False, ""
    return True, "Detected instruction-like manipulation in claim text."


def normalize_issue_type(issue: str) -> str:
    """Normalize a free-form issue into a canonical enum value."""
    if not issue:
        return "unknown"
    cleaned = issue.strip().lower().replace("-", "_").replace(" ", "_")
    if cleaned in VALID_ISSUES:
        return cleaned

    plain = issue.strip().lower()
    for canonical, keywords in ISSUE_KEYWORDS:
        if any(_contains_phrase(plain, keyword) for keyword in keywords):
            return canonical
    return "unknown"


def extract_claim_signals(claim_text: str, claim_object: str) -> ClaimSignals:
    """Extract part and issue cues from the claim conversation deterministically."""
    lower = claim_text.lower()
    parts = _extract_parts(lower, claim_object)
    primary_part = parts[0] if parts else "unknown"
    secondary_targets = parts[1:]
    issue_hypothesis = _extract_issue(lower, claim_object, primary_part)
    has_instruction_text, instruction_text_detail = detect_instruction_text(claim_text)
    language_notes = "hinglish" if is_multilingual_claim(claim_text) else "english"

    confidence = 0.55
    if primary_part != "unknown":
        confidence += 0.2
    if issue_hypothesis != "unknown":
        confidence += 0.15
    if language_notes != "english":
        confidence -= 0.05

    return ClaimSignals(
        primary_part=primary_part,
        issue_hypothesis=issue_hypothesis,
        secondary_targets=secondary_targets,
        has_instruction_text=has_instruction_text,
        instruction_text_detail=instruction_text_detail,
        language_notes=language_notes,
        confidence=max(0.3, min(confidence, 0.95)),
    )


def part_matches_claim(claimed_part: str, observed_part: str, claim_object: str) -> bool:
    """Check whether an observed part is close enough to the claimed part."""
    claimed = normalize_object_part(claimed_part, claim_object)
    observed = normalize_object_part(observed_part, claim_object)
    if claimed == "unknown" or observed == "unknown":
        return False
    if claimed == observed:
        return True

    body_like = BODY_LIKE_PARTS.get(claim_object, set())
    if claimed == "body" and observed in body_like:
        return True
    if observed == "body" and claimed in body_like:
        return True
    return False


def issue_matches_claim(claimed_issue: str, observed_issue: str) -> bool:
    """Check whether the observed issue is compatible with the claimed issue family."""
    claimed = normalize_issue_type(claimed_issue)
    observed = normalize_issue_type(observed_issue)
    if claimed == "unknown" or observed == "unknown":
        return False
    return observed in ISSUE_COMPATIBILITY.get(claimed, {claimed})


def build_mismatch_notes(
    *,
    claim_object: str,
    claimed_part: str,
    claimed_issue: str,
    object_visible: bool,
    object_type_seen: str,
    part_seen: str,
    issue_observed: str,
) -> str:
    """Build a concise deterministic mismatch note from normalized facts."""
    if not object_visible:
        return "Claimed object is not clearly visible."

    normalized_object_type = object_type_seen.strip().lower()
    if normalized_object_type not in ("unknown", claim_object):
        return f"Observed object '{normalized_object_type}' differs from claimed '{claim_object}'."

    if not part_matches_claim(claimed_part, part_seen, claim_object):
        return f"Observed part '{part_seen}' does not match claimed part '{claimed_part}'."

    if issue_observed == "none":
        return f"Claimed part '{claimed_part}' is visible but no damage is visible."

    if issue_observed != "unknown" and not issue_matches_claim(claimed_issue, issue_observed):
        return f"Observed issue '{issue_observed}' differs from claimed issue '{claimed_issue}'."

    return ""


def _extract_parts(text: str, claim_object: str) -> list[str]:
    found: list[tuple[int, str]] = []
    for canonical, keywords in PART_KEYWORDS.get(claim_object, []):
        positions = [
            position
            for keyword in keywords
            for position in _find_phrase_positions(text, keyword)
            if not _is_negated_mention(text, position, keyword)
        ]
        if positions:
            found.append((min(positions), canonical))

    # Prefer more specific rear/front bumper over generic body-like references.
    deduped: list[str] = []
    for _, part in sorted(found, key=lambda item: item[0]):
        if part not in deduped:
            deduped.append(part)
    if claim_object == ClaimObject.PACKAGE.value and "contents" in deduped and "item" in deduped:
        deduped = ["contents"] + [part for part in deduped if part != "contents"]
    return deduped


def _extract_issue(text: str, claim_object: str, primary_part: str) -> str:
    for canonical, keywords in ISSUE_KEYWORDS:
        if any(_contains_phrase(text, keyword) for keyword in keywords):
            if canonical == "water_damage" and claim_object == ClaimObject.LAPTOP.value and primary_part == "keyboard":
                return "stain"
            return canonical
    if primary_part == "side_mirror" and "damage" in text:
        return "broken_part"
    return "unknown"


def _contains_phrase(text: str, phrase: str) -> bool:
    return any(True for _ in _find_phrase_positions(text, phrase))


def _find_phrase_positions(text: str, phrase: str) -> list[int]:
    pattern = re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)")
    return [match.start() for match in pattern.finditer(text)]


def _is_negated_mention(text: str, position: int, phrase: str) -> bool:
    before = text[max(0, position - 40):position]
    after = text[position:position + max(60, len(phrase) + 40)]
    if re.search(r"\b(?:not|no)\b[^.?!;:]{0,30}$", before):
        return True
    if re.search(r"\bnot (?:exactly|my main concern|the issue|the main concern)\b", after):
        return True
    return False
