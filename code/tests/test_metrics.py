"""
Unit tests for the evaluation metrics module.
"""
from __future__ import annotations

import pytest
from evaluation import evaluate_predictions as exported_evaluate_predictions
from evaluation.metrics import (
    parse_set_field,
    normalize_bool,
    normalize_field_value,
    calculate_set_precision_recall_f1,
    check_row_match,
    evaluate_predictions,
)


def test_evaluation_package_exports_metrics_api():
    assert exported_evaluate_predictions is evaluate_predictions


def test_parse_set_field():
    assert parse_set_field("none") == set()
    assert parse_set_field("wrong_object;claim_mismatch") == {"wrong_object", "claim_mismatch"}
    assert parse_set_field("  wrong_object ; claim_mismatch  ") == {"wrong_object", "claim_mismatch"}
    assert parse_set_field("") == set()
    assert parse_set_field("none;blurry_image") == {"blurry_image"}


def test_normalize_bool():
    assert normalize_bool(True) == "true"
    assert normalize_bool(False) == "false"
    assert normalize_bool("True") == "true"
    assert normalize_bool("false") == "false"
    assert normalize_bool("yes") == "true"
    assert normalize_bool("0") == "false"


def test_normalize_field_value():
    assert normalize_field_value("evidence_standard_met", "True") == "true"
    assert normalize_field_value("valid_image", "false") == "false"
    # Semicolon sorted risk_flags
    assert normalize_field_value("risk_flags", "wrong_object;blurry_image") == "blurry_image;wrong_object"
    # Semicolon sorted supporting_image_ids (natural sort: img_2 before img_10)
    assert normalize_field_value("supporting_image_ids", "img_10;img_2;img_1") == "img_1;img_2;img_10"
    # General string field
    assert normalize_field_value("claim_status", "  SUPPORTED  ") == "supported"


def test_calculate_set_precision_recall_f1():
    # Both empty (none or empty string)
    assert calculate_set_precision_recall_f1("none", "none") == (1.0, 1.0, 1.0)
    # Gold empty, pred has flags
    assert calculate_set_precision_recall_f1("none", "blurry_image") == (0.0, 1.0, 0.0)
    # Pred empty, gold has flags
    assert calculate_set_precision_recall_f1("blurry_image", "none") == (1.0, 0.0, 0.0)
    # Part overlap
    # Gold: blurry_image, wrong_object (2 items)
    # Pred: wrong_object, claim_mismatch (2 items)
    # Intersection: wrong_object (1 item)
    # Precision: 1/2 = 0.5
    # Recall: 1/2 = 0.5
    # F1: 2 * 0.5 * 0.5 / 1.0 = 0.5
    assert calculate_set_precision_recall_f1(
        "blurry_image;wrong_object", "wrong_object;claim_mismatch"
    ) == (0.5, 0.5, 0.5)


def test_check_row_match():
    gold = {
        "evidence_standard_met": "true",
        "risk_flags": "none",
        "issue_type": "dent",
        "object_part": "rear_bumper",
        "claim_status": "supported",
        "supporting_image_ids": "img_1",
        "valid_image": "true",
        "severity": "medium",
    }
    # Matches exactly (but case/whitespace different)
    pred_ok = {
        "evidence_standard_met": "True ",
        "risk_flags": "none",
        "issue_type": "DENT",
        "object_part": "rear_bumper",
        "claim_status": "supported",
        "supporting_image_ids": "img_1;",
        "valid_image": "true",
        "severity": "medium",
    }
    assert check_row_match(gold, pred_ok) is True

    # One mismatch
    pred_bad = pred_ok.copy()
    pred_bad["severity"] = "high"
    assert check_row_match(gold, pred_bad) is False


def test_evaluate_predictions():
    gold_rows = [
        {
            "user_id": "user_001",
            "claim_object": "car",
            "evidence_standard_met": "true",
            "risk_flags": "none",
            "issue_type": "dent",
            "object_part": "rear_bumper",
            "claim_status": "supported",
            "supporting_image_ids": "img_1",
            "valid_image": "true",
            "severity": "medium",
        },
        {
            "user_id": "user_002",
            "claim_object": "car",
            "evidence_standard_met": "false",
            "risk_flags": "wrong_object;claim_mismatch",
            "issue_type": "broken_part",
            "object_part": "front_bumper",
            "claim_status": "not_enough_information",
            "supporting_image_ids": "img_1;img_2",
            "valid_image": "true",
            "severity": "unknown",
        }
    ]

    # Perfect prediction
    pred_rows_perfect = [
        {
            "user_id": "user_001",
            "claim_object": "car",
            "evidence_standard_met": "true",
            "risk_flags": "none",
            "issue_type": "dent",
            "object_part": "rear_bumper",
            "claim_status": "supported",
            "supporting_image_ids": "img_1",
            "valid_image": "true",
            "severity": "medium",
        },
        {
            "user_id": "user_002",
            "claim_object": "car",
            "evidence_standard_met": "false",
            # Out of order risk_flags, shouldn't matter
            "risk_flags": "claim_mismatch;wrong_object",
            "issue_type": "broken_part",
            "object_part": "front_bumper",
            "claim_status": "not_enough_information",
            "supporting_image_ids": "img_2;img_1",
            "valid_image": "true",
            "severity": "unknown",
        }
    ]

    metrics = evaluate_predictions(gold_rows, pred_rows_perfect)
    assert metrics["exact_matches"] == 2
    assert metrics["exact_match_rate"] == 1.0
    assert metrics["field_accuracies"]["severity"] == 1.0
    assert metrics["risk_flags_metrics"]["f1"] == 1.0
    assert metrics["supporting_image_ids_metrics"]["f1"] == 1.0

    # Partially wrong prediction
    pred_rows_partial = [
        {
            "user_id": "user_001",
            "claim_object": "car",
            "evidence_standard_met": "true",
            "risk_flags": "none",
            "issue_type": "scratch",  # mismatch (dent vs scratch)
            "object_part": "rear_bumper",
            "claim_status": "supported",
            "supporting_image_ids": "img_1",
            "valid_image": "true",
            "severity": "medium",
        },
        {
            "user_id": "user_002",
            "claim_object": "car",
            "evidence_standard_met": "false",
            "risk_flags": "wrong_object",  # partial mismatch (missing claim_mismatch)
            "issue_type": "broken_part",
            "object_part": "front_bumper",
            "claim_status": "not_enough_information",
            "supporting_image_ids": "img_1;img_2",
            "valid_image": "true",
            "severity": "unknown",
        }
    ]

    metrics_partial = evaluate_predictions(gold_rows, pred_rows_partial)
    assert metrics_partial["exact_matches"] == 0
    assert metrics_partial["exact_match_rate"] == 0.0
    # Field accuracy for issue_type is 0.5 (1/2 matched)
    assert metrics_partial["field_accuracies"]["issue_type"] == 0.5
    # Risk flags F1 calculation:
    # Row 1: gold none, pred none -> 1.0 F1
    # Row 2: gold wrong_object;claim_mismatch, pred wrong_object -> Precision = 1/1 = 1.0, Recall = 1/2 = 0.5, F1 = 2 * 1 * 0.5 / 1.5 = 2/3 = 0.6666...
    # Avg F1: (1.0 + 0.6666) / 2 = 0.8333...
    assert pytest.approx(metrics_partial["risk_flags_metrics"]["f1"]) == 0.8333333333333334
