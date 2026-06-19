"""
Canonical schemas and enums for the claims verification system.
Single source of truth for all allowed values, input/output models,
and intermediate pipeline data structures.
"""
from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator


# ── Canonical Enums ──────────────────────────────────────────────────


class ClaimObject(str, Enum):
    CAR = "car"
    LAPTOP = "laptop"
    PACKAGE = "package"


class ClaimStatus(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    NOT_ENOUGH_INFORMATION = "not_enough_information"


class IssueType(str, Enum):
    DENT = "dent"
    SCRATCH = "scratch"
    CRACK = "crack"
    GLASS_SHATTER = "glass_shatter"
    BROKEN_PART = "broken_part"
    MISSING_PART = "missing_part"
    TORN_PACKAGING = "torn_packaging"
    CRUSHED_PACKAGING = "crushed_packaging"
    WATER_DAMAGE = "water_damage"
    STAIN = "stain"
    NONE = "none"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


# Object part enums per claim object
class CarPart(str, Enum):
    FRONT_BUMPER = "front_bumper"
    REAR_BUMPER = "rear_bumper"
    DOOR = "door"
    HOOD = "hood"
    WINDSHIELD = "windshield"
    SIDE_MIRROR = "side_mirror"
    HEADLIGHT = "headlight"
    TAILLIGHT = "taillight"
    FENDER = "fender"
    QUARTER_PANEL = "quarter_panel"
    BODY = "body"
    UNKNOWN = "unknown"


class LaptopPart(str, Enum):
    SCREEN = "screen"
    KEYBOARD = "keyboard"
    TRACKPAD = "trackpad"
    HINGE = "hinge"
    LID = "lid"
    CORNER = "corner"
    PORT = "port"
    BASE = "base"
    BODY = "body"
    UNKNOWN = "unknown"


class PackagePart(str, Enum):
    BOX = "box"
    PACKAGE_CORNER = "package_corner"
    PACKAGE_SIDE = "package_side"
    SEAL = "seal"
    LABEL = "label"
    CONTENTS = "contents"
    ITEM = "item"
    UNKNOWN = "unknown"


class RiskFlag(str, Enum):
    """Risk flags in canonical order from problem_statement.md."""
    NONE = "none"
    BLURRY_IMAGE = "blurry_image"
    CROPPED_OR_OBSTRUCTED = "cropped_or_obstructed"
    LOW_LIGHT_OR_GLARE = "low_light_or_glare"
    WRONG_ANGLE = "wrong_angle"
    WRONG_OBJECT = "wrong_object"
    WRONG_OBJECT_PART = "wrong_object_part"
    DAMAGE_NOT_VISIBLE = "damage_not_visible"
    CLAIM_MISMATCH = "claim_mismatch"
    POSSIBLE_MANIPULATION = "possible_manipulation"
    NON_ORIGINAL_IMAGE = "non_original_image"
    TEXT_INSTRUCTION_PRESENT = "text_instruction_present"
    USER_HISTORY_RISK = "user_history_risk"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


# Canonical ordering for risk flags (for deterministic serialization)
RISK_FLAG_ORDER = [rf.value for rf in RiskFlag if rf != RiskFlag.NONE]

# All valid object parts by claim object
OBJECT_PARTS = {
    ClaimObject.CAR: {p.value for p in CarPart},
    ClaimObject.LAPTOP: {p.value for p in LaptopPart},
    ClaimObject.PACKAGE: {p.value for p in PackagePart},
}


def get_valid_parts(claim_object: str) -> set[str]:
    """Return the set of valid part names for a claim object."""
    try:
        obj = ClaimObject(claim_object)
        return OBJECT_PARTS[obj]
    except (ValueError, KeyError):
        return {"unknown"}


def normalize_object_part(part: str, claim_object: str) -> str:
    """Normalize an object part string to its canonical value."""
    part = part.strip().lower().replace(" ", "_").replace("-", "_")
    valid = get_valid_parts(claim_object)
    if part in valid:
        return part
    return "unknown"


def serialize_risk_flags(flags: list[str]) -> str:
    """Serialize risk flags in canonical order, deduped."""
    if not flags or flags == ["none"]:
        return "none"
    # Normalize
    normalized = set()
    for f in flags:
        f = f.strip().lower()
        if f and f != "none":
            normalized.add(f)
    if not normalized:
        return "none"
    # Sort by canonical order
    ordered = sorted(normalized, key=lambda x: RISK_FLAG_ORDER.index(x) if x in RISK_FLAG_ORDER else len(RISK_FLAG_ORDER))
    return ";".join(ordered)


def serialize_image_ids(ids: list[str]) -> str:
    """Serialize image IDs as semicolon-separated stems, deterministic order."""
    if not ids or ids == ["none"]:
        return "none"
    clean: set[str] = set()
    for img_id in ids:
        stem = Path(img_id.strip()).stem
        if stem and stem != "none":
            clean.add(stem)
    if not clean:
        return "none"
    return ";".join(sorted(clean, key=_image_id_sort_key))


def _image_id_sort_key(image_id: str) -> tuple[str, int, str]:
    """Sort image IDs naturally, for example img_2 before img_10."""
    match = re.match(r"^(.*?)(\d+)$", image_id)
    if not match:
        return (image_id, -1, image_id)
    prefix, number = match.groups()
    return (prefix, int(number), image_id)


# ── Input Schemas ────────────────────────────────────────────────────


class ClaimInput(BaseModel):
    """A single row from claims.csv."""
    user_id: str
    image_paths: str
    user_claim: str
    claim_object: str

    @field_validator("claim_object")
    @classmethod
    def validate_claim_object(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in {e.value for e in ClaimObject}:
            raise ValueError(f"Invalid claim_object: {v}")
        return v

    def get_image_path_list(self) -> list[str]:
        """Split semicolon-separated image paths."""
        return [p.strip() for p in self.image_paths.split(";") if p.strip()]

    def get_image_ids(self) -> list[str]:
        """Extract image IDs (filename stems) from paths."""
        from pathlib import Path as P
        return [P(p.strip()).stem for p in self.image_paths.split(";") if p.strip()]


class UserHistory(BaseModel):
    """A row from user_history.csv."""
    user_id: str
    past_claim_count: int
    accept_claim: int
    manual_review_claim: int
    rejected_claim: int
    last_90_days_claim_count: int
    history_flags: str
    history_summary: str

    def has_risk(self) -> bool:
        """Check if user has risk flags."""
        return self.history_flags.strip().lower() != "none"

    def get_flag_list(self) -> list[str]:
        """Parse history flags into a list."""
        if self.history_flags.strip().lower() == "none":
            return []
        return [f.strip() for f in self.history_flags.split(";") if f.strip()]


class EvidenceRequirement(BaseModel):
    """A row from evidence_requirements.csv."""
    requirement_id: str
    claim_object: str
    applies_to: str
    minimum_image_evidence: str


# ── Intermediate Schemas ─────────────────────────────────────────────


class ParsedClaim(BaseModel):
    """Stage 1 output: structured extraction from user claim text."""
    primary_object: str = Field(description="The main object being claimed (car/laptop/package)")
    primary_part: str = Field(description="The specific part the user is claiming about")
    issue_hypothesis: str = Field(description="What the user thinks is wrong")
    secondary_targets: list[str] = Field(default_factory=list, description="Any secondary parts mentioned")
    has_instruction_text: bool = Field(default=False, description="Whether the claim contains instruction-like manipulation")
    instruction_text_detail: str = Field(default="", description="Detail about any instruction text found")
    language_notes: str = Field(default="english", description="Primary language or multilingual note")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Parser confidence")


class ImageObservation(BaseModel):
    """Stage 2 output: per-image structured evidence extraction."""
    image_id: str = Field(description="Image filename stem like img_1")
    object_visible: bool = Field(description="Whether the claimed object type is visible")
    object_type_seen: str = Field(default="unknown", description="What object type is actually visible")
    relevant_part_visible: bool = Field(description="Whether the claimed part is visible")
    part_seen: str = Field(default="unknown", description="What part is actually visible")
    issue_observed: str = Field(default="unknown", description="What issue/damage is observed")
    issue_matches_claim: bool = Field(default=False, description="Whether observed issue matches claimed issue")
    severity_estimate: str = Field(default="unknown", description="none/low/medium/high/unknown")
    quality_issues: list[str] = Field(default_factory=list, description="Image quality problems")
    is_usable: bool = Field(default=True, description="Whether image is usable for review")
    mismatch_notes: str = Field(default="", description="Any object/part/claim mismatch notes")
    has_text_instruction: bool = Field(default=False, description="Whether image contains instruction text")
    authenticity_concern: bool = Field(default=False, description="Whether image appears non-original")
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    raw_description: str = Field(default="", description="Free-text description of what is seen")


class AggregatedEvidence(BaseModel):
    """Aggregated evidence across all images for a claim."""
    claim_input: ClaimInput
    parsed_claim: ParsedClaim
    observations: list[ImageObservation]
    user_history: Optional[UserHistory] = None

    # Aggregated signals
    any_object_visible: bool = False
    any_part_visible: bool = False
    best_issue_observed: str = "unknown"
    best_severity: str = "unknown"
    any_mismatch: bool = False
    any_quality_issue: bool = False
    any_text_instruction: bool = False
    any_authenticity_concern: bool = False
    all_images_usable: bool = True
    supporting_image_ids: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    evidence_sufficient: bool = False
    confidence: float = 0.5
    escalation_reasons: list[str] = Field(default_factory=list)


# ── Output Schema ────────────────────────────────────────────────────

# Column order must match problem_statement.md exactly
OUTPUT_COLUMNS = [
    "user_id",
    "image_paths",
    "user_claim",
    "claim_object",
    "evidence_standard_met",
    "evidence_standard_met_reason",
    "risk_flags",
    "issue_type",
    "object_part",
    "claim_status",
    "claim_status_justification",
    "supporting_image_ids",
    "valid_image",
    "severity",
]


class ClaimOutput(BaseModel):
    """Final output row for output.csv."""
    user_id: str
    image_paths: str
    user_claim: str
    claim_object: str
    evidence_standard_met: str  # "true" or "false"
    evidence_standard_met_reason: str
    risk_flags: str  # semicolon-separated or "none"
    issue_type: str
    object_part: str
    claim_status: str
    claim_status_justification: str
    supporting_image_ids: str  # semicolon-separated or "none"
    valid_image: str  # "true" or "false"
    severity: str

    @field_validator("claim_object")
    @classmethod
    def validate_output_claim_object(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in {e.value for e in ClaimObject}:
            raise ValueError(f"Invalid claim_object: {v}")
        return v

    @field_validator("evidence_standard_met", "valid_image")
    @classmethod
    def validate_bool_string(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("true", "false"):
            raise ValueError(f"Boolean field must be 'true' or 'false', got: {v}")
        return v

    @field_validator("claim_status")
    @classmethod
    def validate_claim_status(cls, v: str) -> str:
        v = v.strip().lower()
        valid = {e.value for e in ClaimStatus}
        if v not in valid:
            raise ValueError(f"Invalid claim_status: {v}. Must be one of {valid}")
        return v

    @field_validator("issue_type")
    @classmethod
    def validate_issue_type(cls, v: str) -> str:
        v = v.strip().lower()
        valid = {e.value for e in IssueType}
        if v not in valid:
            raise ValueError(f"Invalid issue_type: {v}. Must be one of {valid}")
        return v

    @field_validator("risk_flags")
    @classmethod
    def validate_risk_flags(cls, v: str) -> str:
        parts = [part.strip().lower() for part in v.split(";") if part.strip()]
        if not parts:
            return "none"
        if parts == ["none"]:
            return "none"

        valid = {flag.value for flag in RiskFlag}
        invalid = [part for part in parts if part not in valid or part == "none"]
        if invalid:
            raise ValueError(f"Invalid risk_flags: {invalid}")
        return serialize_risk_flags(parts)

    @field_validator("object_part")
    @classmethod
    def validate_object_part(cls, v: str, info: ValidationInfo) -> str:
        claim_object = info.data.get("claim_object")
        if not claim_object:
            raise ValueError("claim_object must be validated before object_part")

        normalized = v.strip().lower().replace(" ", "_").replace("-", "_")
        valid_parts = get_valid_parts(claim_object)
        if normalized not in valid_parts:
            raise ValueError(
                f"Invalid object_part '{normalized}' for claim_object '{claim_object}'"
            )
        return normalized

    @field_validator("supporting_image_ids")
    @classmethod
    def validate_supporting_image_ids(cls, v: str) -> str:
        parts = [part.strip() for part in v.split(";") if part.strip()]
        return serialize_image_ids(parts)

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        v = v.strip().lower()
        valid = {e.value for e in Severity}
        if v not in valid:
            raise ValueError(f"Invalid severity: {v}. Must be one of {valid}")
        return v

    def to_row_dict(self) -> dict[str, str]:
        """Return a dict with keys in canonical OUTPUT_COLUMNS order."""
        d = self.model_dump()
        return {col: str(d[col]) for col in OUTPUT_COLUMNS}
