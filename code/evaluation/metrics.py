"""
Core metric definitions and helper functions for evaluation.
Defines exact match, field accuracy, and set-based precision/recall/F1 metrics.
"""
from __future__ import annotations

from typing import Any

from src.schemas import (
    serialize_risk_flags,
    serialize_image_ids,
)

DECISION_FIELDS = [
    "evidence_standard_met",
    "risk_flags",
    "issue_type",
    "object_part",
    "claim_status",
    "supporting_image_ids",
    "valid_image",
    "severity",
]


def parse_set_field(val: str) -> set[str]:
    """Parse a semicolon-separated string into a set of normalized elements, ignoring 'none'."""
    if not val:
        return set()
    parts = [p.strip().lower() for p in val.split(";") if p.strip()]
    return {p for p in parts if p and p != "none"}


def normalize_bool(val: str | bool) -> str:
    """Normalize a boolean or boolean string to lowercase 'true' or 'false'."""
    if isinstance(val, bool):
        return "true" if val else "false"
    s = str(val).strip().lower()
    return "true" if s in ("true", "yes", "1") else "false"


def normalize_field_value(field_name: str, val: Any) -> Any:
    """Normalize a field value depending on its type for comparison."""
    if field_name in ("evidence_standard_met", "valid_image"):
        return normalize_bool(val)
    elif field_name in ("risk_flags", "supporting_image_ids"):
        # Return sorted, canonicalized string representation for comparison
        parsed = parse_set_field(str(val))
        if field_name == "risk_flags":
            return serialize_risk_flags(list(parsed))
        else:
            return serialize_image_ids(list(parsed))
    else:
        # Default string normalization
        return str(val).strip().lower() if val is not None else ""


def calculate_set_precision_recall_f1(gold_val: str, pred_val: str) -> tuple[float, float, float]:
    """Compute precision, recall, and F1-score between two semicolon-separated list fields."""
    gold_set = parse_set_field(gold_val)
    pred_set = parse_set_field(pred_val)

    if not gold_set and not pred_set:
        return 1.0, 1.0, 1.0
    if not gold_set:
        # Gold has no flags/images, so if we predicted none, that's correct (handled above).
        # If we predicted something, precision is 0.0, and recall is 1.0 (found all 0 gold elements).
        return 0.0, 1.0, 0.0
    if not pred_set:
        # Pred has no flags/images, but gold does. Precision is 1.0, recall is 0.0.
        return 1.0, 0.0, 0.0

    intersection = gold_set.intersection(pred_set)
    precision = len(intersection) / len(pred_set)
    recall = len(intersection) / len(gold_set)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return precision, recall, f1


def check_row_match(gold: dict[str, Any], pred: dict[str, Any], fields: list[str] = DECISION_FIELDS) -> bool:
    """Check if a single row matches gold on all specified decision fields."""
    for field in fields:
        if field not in gold or field not in pred:
            return False
        g_norm = normalize_field_value(field, gold[field])
        p_norm = normalize_field_value(field, pred[field])
        if g_norm != p_norm:
            return False
    return True


def evaluate_predictions(gold_rows: list[dict[str, Any]], pred_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare a list of predictions against gold labels and calculate aggregate metrics.

    Assumes rows match in order or can be aligned by user_id and claim_object.
    """
    # Build maps to align rows safely
    gold_map = {(r["user_id"], r["claim_object"]): r for r in gold_rows}
    pred_map = {(r["user_id"], r["claim_object"]): r for r in pred_rows}

    aligned_keys = []
    for key in gold_map:
        if key in pred_map:
            aligned_keys.append(key)

    if not aligned_keys:
        raise ValueError("Could not align predictions with gold labels using (user_id, claim_object) keys.")

    total_rows = len(aligned_keys)
    exact_matches = 0

    # Secondary field-level accuracy trackers
    field_correct = {f: 0 for f in DECISION_FIELDS}
    
    # Cumulative set metrics
    rf_precision_sum, rf_recall_sum, rf_f1_sum = 0.0, 0.0, 0.0
    img_precision_sum, img_recall_sum, img_f1_sum = 0.0, 0.0, 0.0

    mismatches = []

    for key in aligned_keys:
        gold = gold_map[key]
        pred = pred_map[key]

        # Exact match check
        row_matched = check_row_match(gold, pred, DECISION_FIELDS)
        if row_matched:
            exact_matches += 1

        row_mismatched_fields = {}
        # Field accuracy check
        for field in DECISION_FIELDS:
            g_norm = normalize_field_value(field, gold[field])
            p_norm = normalize_field_value(field, pred[field])
            if g_norm == p_norm:
                field_correct[field] += 1
            else:
                row_mismatched_fields[field] = (gold[field], pred[field])

        if row_mismatched_fields:
            mismatches.append({
                "user_id": key[0],
                "claim_object": key[1],
                "mismatched_fields": row_mismatched_fields,
                "gold_justification": gold.get("claim_status_justification", ""),
                "pred_justification": pred.get("claim_status_justification", ""),
            })

        # Set metric calculations
        rf_p, rf_r, rf_f1 = calculate_set_precision_recall_f1(gold["risk_flags"], pred["risk_flags"])
        rf_precision_sum += rf_p
        rf_recall_sum += rf_r
        rf_f1_sum += rf_f1

        img_p, img_r, img_f1 = calculate_set_precision_recall_f1(gold["supporting_image_ids"], pred["supporting_image_ids"])
        img_precision_sum += img_p
        img_recall_sum += img_r
        img_f1_sum += img_f1

    # Aggregate summaries
    exact_match_rate = exact_matches / total_rows if total_rows > 0 else 0.0
    field_accuracies = {f: (field_correct[f] / total_rows) for f in DECISION_FIELDS}

    return {
        "total_evaluated": total_rows,
        "exact_matches": exact_matches,
        "exact_match_rate": exact_match_rate,
        "field_accuracies": field_accuracies,
        "risk_flags_metrics": {
            "precision": rf_precision_sum / total_rows,
            "recall": rf_recall_sum / total_rows,
            "f1": rf_f1_sum / total_rows,
        },
        "supporting_image_ids_metrics": {
            "precision": img_precision_sum / total_rows,
            "recall": img_recall_sum / total_rows,
            "f1": img_f1_sum / total_rows,
        },
        "mismatches": mismatches,
        "aligned_keys": aligned_keys,
        "gold_map": gold_map,
        "pred_map": pred_map,
    }
