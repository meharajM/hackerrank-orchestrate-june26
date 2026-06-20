# Evaluation Report — Damage Claim Verification System

## Metadata
- **Strategy Name:** dynamic_run_strategy_B
- **Model/Adapter:** Ollama (qwen3-vl:4b)
- **Total Claims Evaluated:** 1
- **Notes:** Single-claim real Ollama smoke

## Headline Summary
| Metric | Score | Matches | Details |
|---|---|---|---|
| **Row Exact Match** | **0.0%** | 0/1 | Decided over all 8 core decision fields |
| **Risk Flags F1-Score** | **0.0%** | - | Precision: 0.00, Recall: 1.00 |
| **Supporting Images F1-Score** | **0.0%** | - | Precision: 1.00, Recall: 0.00 |

## Per-Field Accuracy
| Field Name | Accuracy | Correct |
|---|---|---|
| `object_part` | 100.0% | 1/1 |
| `evidence_standard_met` | 0.0% | 0/1 |
| `risk_flags` | 0.0% | 0/1 |
| `issue_type` | 0.0% | 0/1 |
| `claim_status` | 0.0% | 0/1 |
| `supporting_image_ids` | 0.0% | 0/1 |
| `valid_image` | 0.0% | 0/1 |
| `severity` | 0.0% | 0/1 |

## Slice Analysis
| Slice Category | Group | Count | Exact Match | Risk Flags F1 | Supporting Images F1 |
|---|---|---|---|---|---|
| **Claim Object** | | | | | |
| - | Car | 1 | 0.0% | 0.0% | 0.0% |
| - | Laptop | 0 | 0.0% | 0.0% | 0.0% |
| - | Package | 0 | 0.0% | 0.0% | 0.0% |
| **Image Count** | | | | | |
| - | 1 Image | 1 | 0.0% | 0.0% | 0.0% |
| - | 2+ Images | 0 | 0.0% | 0.0% | 0.0% |
| **Claim Status (Gold)** | | | | | |
| - | Supported | 1 | 0.0% | 0.0% | 0.0% |
| - | Contradicted | 0 | 0.0% | 0.0% | 0.0% |
| - | Not Enough Info | 0 | 0.0% | 0.0% | 0.0% |
| **History Risk (Gold)** | | | | | |
| - | Has Risk Flag | 0 | 0.0% | 0.0% | 0.0% |
| - | No Risk Flag | 1 | 0.0% | 0.0% | 0.0% |
| **Language Status** | | | | | |
| - | Multilingual (Hinglish) | 0 | 0.0% | 0.0% | 0.0% |
| - | English | 1 | 0.0% | 0.0% | 0.0% |

## Error Details / Mismatches
Found 1 mismatched row(s). Details below:

### 1. User: `user_001` (Object: `car`)
**Mismatched fields:**
- **evidence_standard_met**: Gold=`true` | Pred=`false`
- **risk_flags**: Gold=`none` | Pred=`blurry_image`
- **issue_type**: Gold=`dent` | Pred=`unknown`
- **claim_status**: Gold=`supported` | Pred=`not_enough_information`
- **supporting_image_ids**: Gold=`img_1` | Pred=`none`
- **valid_image**: Gold=`true` | Pred=`false`
- **severity**: Gold=`medium` | Pred=`unknown`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image clearly shows a dent on the rear bumper and the user history does not add risk. |
| **Pred Justification** | Not enough information because all submitted images are unusable due to quality issues (e.g., blurry, dark, low visibility). |
