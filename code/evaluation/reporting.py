"""
Reporting and formatting utilities for evaluation.
Generates human-readable markdown summaries and slice metrics.
"""
from __future__ import annotations

import re
from typing import Any
from pathlib import Path

from .metrics import (
    check_row_match,
    calculate_set_precision_recall_f1,
    parse_set_field,
)


def is_multilingual_claim(claim_text: str) -> bool:
    """Detect if a claim has Hinglish/Hindi or multilingual elements based on keyword presence."""
    hinglish_words = {"mein", "meri", "hua", "toh", "phati", "kar", "nahi", "pe", "ko", "par", "hai", "ke", "upar", "theek"}
    words = set(re.findall(r"\b[a-zA-Z]+\b", claim_text.lower()))
    return len(words.intersection(hinglish_words)) >= 2


def generate_slice_metrics(results: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Compute metrics grouped by different logical slices of the dataset."""
    gold_map = results["gold_map"]
    pred_map = results["pred_map"]
    aligned_keys = results["aligned_keys"]

    # Define slice groups
    slices: dict[str, list[tuple[str, str]]] = {
        # claim_object slices
        "obj:car": [],
        "obj:laptop": [],
        "obj:package": [],
        # image count slices
        "imgs:1": [],
        "imgs:2+": [],
        # claim status slices
        "status:supported": [],
        "status:contradicted": [],
        "status:not_enough_info": [],
        # history risk slices
        "history:has_risk": [],
        "history:no_risk": [],
        # multilingual slices
        "lang:multilingual": [],
        "lang:english": [],
    }

    # Categorize keys
    for key in aligned_keys:
        gold = gold_map[key]
        
        # 1. claim_object
        obj = key[1]
        if f"obj:{obj}" in slices:
            slices[f"obj:{obj}"].append(key)
            
        # 2. image count
        image_paths = gold.get("image_paths", "")
        img_count = len([p for p in image_paths.split(";") if p.strip()])
        if img_count == 1:
            slices["imgs:1"].append(key)
        else:
            slices["imgs:2+"].append(key)
            
        # 3. claim status
        status = gold.get("claim_status", "")
        if status == "supported":
            slices["status:supported"].append(key)
        elif status == "contradicted":
            slices["status:contradicted"].append(key)
        elif status == "not_enough_information":
            slices["status:not_enough_info"].append(key)
            
        # 4. history risk
        gold_flags = parse_set_field(gold.get("risk_flags", ""))
        if "user_history_risk" in gold_flags:
            slices["history:has_risk"].append(key)
        else:
            slices["history:no_risk"].append(key)
            
        # 5. multilingual claim
        user_claim = gold.get("user_claim", "")
        if is_multilingual_claim(user_claim):
            slices["lang:multilingual"].append(key)
        else:
            slices["lang:english"].append(key)

    # Calculate metrics per slice
    slice_results = {}
    for slice_name, keys in slices.items():
        if not keys:
            slice_results[slice_name] = {
                "count": 0,
                "exact_match_rate": 0.0,
                "risk_flags_f1": 0.0,
                "supporting_images_f1": 0.0,
            }
            continue
            
        count = len(keys)
        matches = 0
        rf_f1_sum = 0.0
        img_f1_sum = 0.0
        
        for key in keys:
            gold = gold_map[key]
            pred = pred_map[key]
            if check_row_match(gold, pred):
                matches += 1
                
            _, _, rf_f1 = calculate_set_precision_recall_f1(gold["risk_flags"], pred["risk_flags"])
            rf_f1_sum += rf_f1
            
            _, _, img_f1 = calculate_set_precision_recall_f1(gold["supporting_image_ids"], pred["supporting_image_ids"])
            img_f1_sum += img_f1
            
        slice_results[slice_name] = {
            "count": count,
            "exact_match_rate": matches / count,
            "risk_flags_f1": rf_f1_sum / count,
            "supporting_images_f1": img_f1_sum / count,
        }
        
    return slice_results


def build_markdown_report(
    results: dict[str, Any],
    slice_metrics: dict[str, dict[str, Any]],
    strategy_name: str,
    model_version: str,
    notes: str = "",
) -> str:
    """Build the final markdown evaluation report string."""
    total_evaluated = results["total_evaluated"]
    exact_matches = results["exact_matches"]
    exact_match_rate = results["exact_match_rate"]
    
    rf_metrics = results["risk_flags_metrics"]
    img_metrics = results["supporting_image_ids_metrics"]
    
    report = []
    
    report.append(f"# Evaluation Report — Damage Claim Verification System\n")
    report.append(f"## Metadata")
    report.append(f"- **Strategy Name:** {strategy_name}")
    report.append(f"- **Model/Adapter:** {model_version}")
    report.append(f"- **Total Claims Evaluated:** {total_evaluated}")
    if notes:
        report.append(f"- **Notes:** {notes}")
    report.append("")
    
    report.append(f"## Headline Summary")
    report.append(f"| Metric | Score | Matches | Details |")
    report.append(f"|---|---|---|---|")
    report.append(f"| **Row Exact Match** | **{exact_match_rate * 100:.1f}%** | {exact_matches}/{total_evaluated} | Decided over all 8 core decision fields |")
    report.append(f"| **Risk Flags F1-Score** | **{rf_metrics['f1'] * 100:.1f}%** | - | Precision: {rf_metrics['precision']:.2f}, Recall: {rf_metrics['recall']:.2f} |")
    report.append(f"| **Supporting Images F1-Score** | **{img_metrics['f1'] * 100:.1f}%** | - | Precision: {img_metrics['precision']:.2f}, Recall: {img_metrics['recall']:.2f} |")
    report.append("")

    report.append(f"## Per-Field Accuracy")
    report.append(f"| Field Name | Accuracy | Correct |")
    report.append(f"|---|---|---|")
    for field, acc in sorted(results["field_accuracies"].items(), key=lambda x: -x[1]):
        correct = int(round(acc * total_evaluated))
        report.append(f"| `{field}` | {acc * 100:.1f}% | {correct}/{total_evaluated} |")
    report.append("")

    report.append(f"## Slice Analysis")
    report.append(f"| Slice Category | Group | Count | Exact Match | Risk Flags F1 | Supporting Images F1 |")
    report.append(f"|---|---|---|---|---|---|")
    
    # Helper to append slice row
    def append_slice_row(category: str, label: str, slice_key: str):
        m = slice_metrics.get(slice_key, {"count": 0, "exact_match_rate": 0.0, "risk_flags_f1": 0.0, "supporting_images_f1": 0.0})
        report.append(f"| {category} | {label} | {m['count']} | {m['exact_match_rate'] * 100:.1f}% | {m['risk_flags_f1'] * 100:.1f}% | {m['supporting_images_f1'] * 100:.1f}% |")

    report.append(f"| **Claim Object** | | | | | |")
    append_slice_row("-", "Car", "obj:car")
    append_slice_row("-", "Laptop", "obj:laptop")
    append_slice_row("-", "Package", "obj:package")
    
    report.append(f"| **Image Count** | | | | | |")
    append_slice_row("-", "1 Image", "imgs:1")
    append_slice_row("-", "2+ Images", "imgs:2+")
    
    report.append(f"| **Claim Status (Gold)** | | | | | |")
    append_slice_row("-", "Supported", "status:supported")
    append_slice_row("-", "Contradicted", "status:contradicted")
    append_slice_row("-", "Not Enough Info", "status:not_enough_info")
    
    report.append(f"| **History Risk (Gold)** | | | | | |")
    append_slice_row("-", "Has Risk Flag", "history:has_risk")
    append_slice_row("-", "No Risk Flag", "history:no_risk")
    
    report.append(f"| **Language Status** | | | | | |")
    append_slice_row("-", "Multilingual (Hinglish)", "lang:multilingual")
    append_slice_row("-", "English", "lang:english")
    report.append("")

    report.append(f"## Error Details / Mismatches")
    mismatches = results["mismatches"]
    if not mismatches:
        report.append("🎉 **No mismatches found! Perfect exact match rate on the evaluated dataset.**")
    else:
        report.append(f"Found {len(mismatches)} mismatched row(s). Details below:")
        report.append("")
        for idx, item in enumerate(mismatches, 1):
            report.append(f"### {idx}. User: `{item['user_id']}` (Object: `{item['claim_object']}`)")
            report.append(f"**Mismatched fields:**")
            for field, (gold_val, pred_val) in item["mismatched_fields"].items():
                report.append(f"- **{field}**: Gold=`{gold_val}` | Pred=`{pred_val}`")
            report.append("")
            report.append(f"| Justification Source | Text |")
            report.append(f"|---|---|")
            report.append(f"| **Gold Justification** | {item['gold_justification']} |")
            report.append(f"| **Pred Justification** | {item['pred_justification']} |")
            report.append("")
            
    return "\n".join(report)
