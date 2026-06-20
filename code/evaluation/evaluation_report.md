# Evaluation Report — Damage Claim Verification System

## Metadata
- **Strategy Name:** Strategy B (staged pipeline)
- **Model/Adapter:** mock (deterministic, no API key required)
- **Total Claims Evaluated:** 20 on sample set, 44 on test set
- **Notes:** Final Phase 6 submission run: mock model, Strategy B, staged pipeline

## Headline Summary
| Metric | Score | Matches | Details |
|---|---|---|---|
| **Row Exact Match** | **15.0%** | 3/20 | Decided over all 8 core decision fields |
| **Risk Flags F1-Score** | **76.0%** | - | Precision: 0.97, Recall: 0.72 |
| **Supporting Images F1-Score** | **80.0%** | - | Precision: 0.75, Recall: 1.00 |

## Per-Field Accuracy
| Field Name | Accuracy | Correct |
|---|---|---|
| `valid_image` | 90.0% | 18/20 |
| `evidence_standard_met` | 80.0% | 16/20 |
| `claim_status` | 65.0% | 13/20 |
| `supporting_image_ids` | 60.0% | 12/20 |
| `risk_flags` | 55.0% | 11/20 |
| `severity` | 55.0% | 11/20 |
| `object_part` | 50.0% | 10/20 |
| `issue_type` | 45.0% | 9/20 |

## Slice Analysis
| Slice Category | Group | Count | Exact Match | Risk Flags F1 | Supporting Images F1 |
|---|---|---|---|---|---|
| **Claim Object** | | | | | |
| - | Car | 8 | 0.0% | 55.8% | 75.0% |
| - | Laptop | 6 | 50.0% | 96.7% | 88.9% |
| - | Package | 6 | 0.0% | 82.1% | 77.8% |
| **Image Count** | | | | | |
| - | 1 Image | 11 | 27.3% | 84.8% | 90.9% |
| - | 2+ Images | 9 | 0.0% | 65.2% | 66.7% |
| **Claim Status (Gold)** | | | | | |
| - | Supported | 12 | 25.0% | 91.7% | 86.1% |
| - | Contradicted | 5 | 0.0% | 75.8% | 93.3% |
| - | Not Enough Info | 3 | 0.0% | 13.3% | 33.3% |
| **History Risk (Gold)** | | | | | |
| - | Has Risk Flag | 6 | 0.0% | 79.8% | 94.4% |
| - | No Risk Flag | 14 | 21.4% | 74.3% | 73.8% |
| **Language Status** | | | | | |
| - | Multilingual (Hinglish) | 2 | 0.0% | 50.0% | 83.3% |
| - | English | 18 | 16.7% | 78.8% | 79.6% |

## Operational Analysis

| Metric | Sample Set (20 claims) | Test Set (44 claims) |
|---|---|---|
| **Model calls (Stage 1 — text)** | 20 | 44 |
| **Model calls (Stage 2 — multimodal)** | 29 (one per image) | 82 (one per image) |
| **Total model calls** | ~49 | ~126 |
| **Images processed** | 29 | 82 |
| **Input tokens (mock)** | 0 (deterministic, no API) | 0 |
| **Output tokens (mock)** | 0 | 0 |
| **Estimated cost (mock)** | $0.00 | $0.00 |
| **Latency** | ~1.5s | ~6.7s |

### Real-model projections (Ollama qwen3-vl:4b local)

| Metric | Estimate |
|---|---|
| **Stage 1 tokens** | ~300 input + ~100 output per call |
| **Stage 2 tokens** | ~1,250 input (incl. image ~750) + ~200 output per image |
| **Total tokens for test set** | ~44×(300+100) + 82×(1250+200) = ~136,400 tokens |
| **Estimated cost** | $0.00 (local Ollama, no API charges) |
| **Estimated latency** | ~5–15s per multimodal call, ~1–3s per text call |
| **Total estimated runtime (test set)** | ~10–25 minutes depending on hardware |

### TPM/RPM and optimization notes

- **Mock mode**: Zero cost, instant. Suitable for schema validation and pipeline testing.
- **Local Ollama**: No rate limits. Bottleneck is GPU memory and inference speed. Use `OLLAMA_NUM_PARALLEL=4` or tune `max_concurrent_requests` in config for throughput.
- **Gemini (hosted)**: Free-tier quota is 1,500 RPM and 1M TPM on `gemini-2.5-flash-lite`. Test set (126 calls) fits well within free quota.
- **Caching**: Content-addressed response cache (enabled by default) avoids redundant model calls on rerun. Cache keyed by prompt + image hash.
- **Retry strategy**: Up to 3 retries with exponential backoff (1s base) on transient failures.
- **Batching**: `process_claim_batch` supports generator-based streaming. Concurrent requests configurable via `max_concurrent_requests`.

### Pricing assumptions (if using hosted Gemini)

| Item | Cost |
|---|---|
| Gemini 2.5 Flash Lite input | $0.015/1M tokens |
| Gemini 2.5 Flash Lite output | $0.06/1M tokens |
| Total test set (projected) | < $0.01 USD |
| Free-tier quota | Sufficient for full test set |

## Error Details / Mismatches
Found 17 mismatched row(s). Details below:

### 1. User: `user_001` (Object: `car`)
**Mismatched fields:**
- **object_part**: Gold=`rear_bumper` | Pred=`body`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image clearly shows a dent on the rear bumper and the user history does not add risk. |
| **Pred Justification** | Claim supported: damage 'dent' observed on 'body' in image img_1. |

### 2. User: `user_002` (Object: `car`)
**Mismatched fields:**
- **evidence_standard_met**: Gold=`false` | Pred=`true`
- **risk_flags**: Gold=`wrong_object;claim_mismatch;manual_review_required` | Pred=`none`
- **issue_type**: Gold=`broken_part` | Pred=`scratch`
- **object_part**: Gold=`front_bumper` | Pred=`body`
- **claim_status**: Gold=`not_enough_information` | Pred=`supported`
- **severity**: Gold=`unknown` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The submitted images do not reliably support the claim because the damaged close-up and the full vehicle view appear to be from different cars. |
| **Pred Justification** | Claim supported: damage 'scratch' observed on 'body' in image img_1. |

### 3. User: `user_004` (Object: `car`)
**Mismatched fields:**
- **supporting_image_ids**: Gold=`img_1` | Pred=`img_1;img_2`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image set supports the claim because the windshield crack is visible in the close-up. |
| **Pred Justification** | Claim supported: damage 'crack' observed on 'windshield' in image img_1. |

### 4. User: `user_007` (Object: `car`)
**Mismatched fields:**
- **issue_type**: Gold=`broken_part` | Pred=`dent`
- **object_part**: Gold=`side_mirror` | Pred=`body`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The submitted image directly shows damage to the claimed side mirror. |
| **Pred Justification** | Claim supported: damage 'broken_part' observed on 'body' in image img_1. |

### 5. User: `user_005` (Object: `car`)
**Mismatched fields:**
- **risk_flags**: Gold=`claim_mismatch;user_history_risk;manual_review_required` | Pred=`user_history_risk;manual_review_required`
- **issue_type**: Gold=`scratch` | Pred=`dent`
- **object_part**: Gold=`rear_bumper` | Pred=`body`
- **claim_status**: Gold=`contradicted` | Pred=`supported`
- **supporting_image_ids**: Gold=`img_1` | Pred=`img_1;img_2`
- **severity**: Gold=`low` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The images show only minor rear bumper scratching, so the severe damage claim is contradicted. User history also shows several rejected claims. |
| **Pred Justification** | Claim supported: damage 'dent' observed on 'body' in image img_1. |

### 6. User: `user_006` (Object: `car`)
**Mismatched fields:**
- **evidence_standard_met**: Gold=`false` | Pred=`true`
- **risk_flags**: Gold=`wrong_angle;damage_not_visible` | Pred=`none`
- **issue_type**: Gold=`unknown` | Pred=`crack`
- **claim_status**: Gold=`not_enough_information` | Pred=`supported`
- **supporting_image_ids**: Gold=`none` | Pred=`img_1`
- **severity**: Gold=`unknown` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The submitted image shows another part of the car and does not provide evidence for the headlight claim. |
| **Pred Justification** | Claim supported: damage 'crack' observed on 'headlight' in image img_1. |

### 7. User: `user_003` (Object: `car`)
**Mismatched fields:**
- **risk_flags**: Gold=`blurry_image` | Pred=`none`
- **supporting_image_ids**: Gold=`img_2` | Pred=`img_1;img_2`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The clearer second image supports the claim by showing a dent on the door. |
| **Pred Justification** | Claim supported: damage 'dent' observed on 'door' in image img_1. |

### 8. User: `user_008` (Object: `car`)
**Mismatched fields:**
- **risk_flags**: Gold=`claim_mismatch;non_original_image;user_history_risk;manual_review_required` | Pred=`user_history_risk;manual_review_required`
- **issue_type**: Gold=`broken_part` | Pred=`scratch`
- **object_part**: Gold=`front_bumper` | Pred=`hood`
- **claim_status**: Gold=`contradicted` | Pred=`supported`
- **valid_image**: Gold=`false` | Pred=`true`
- **severity**: Gold=`high` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image shows severe front-end damage rather than a scratch on the hood, so it does not support the user's hood-scratch claim. |
| **Pred Justification** | Claim supported: damage 'scratch' observed on 'hood' in image img_1. |

### 9. User: `user_010` (Object: `laptop`)
**Mismatched fields:**
- **issue_type**: Gold=`broken_part` | Pred=`crack`
- **supporting_image_ids**: Gold=`img_1` | Pred=`img_1;img_2`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The first image supports the claim because the hinge damage is visible. |
| **Pred Justification** | Claim supported: damage 'broken_part' observed on 'hinge' in image img_1. |

### 10. User: `user_012` (Object: `laptop`)
**Mismatched fields:**
- **supporting_image_ids**: Gold=`img_2` | Pred=`img_1;img_2`
- **severity**: Gold=`low` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image set supports the claim because the corner dent is visible in the close-up. |
| **Pred Justification** | Claim supported: damage 'dent' observed on 'corner' in image img_1. |

### 11. User: `user_020` (Object: `laptop`)
**Mismatched fields:**
- **risk_flags**: Gold=`damage_not_visible;user_history_risk;manual_review_required` | Pred=`user_history_risk;manual_review_required`
- **issue_type**: Gold=`none` | Pred=`crack`
- **claim_status**: Gold=`contradicted` | Pred=`supported`
- **severity**: Gold=`none` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image shows the trackpad area but does not show clear physical damage, so it contradicts the user's physical damage claim. The user's prior claim history also requires review. |
| **Pred Justification** | Claim supported: damage 'crack' observed on 'trackpad' in image img_1. |

### 12. User: `user_015` (Object: `package`)
**Mismatched fields:**
- **issue_type**: Gold=`crushed_packaging` | Pred=`torn_packaging`
- **object_part**: Gold=`package_corner` | Pred=`box`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image directly shows crushing on the claimed package corner. |
| **Pred Justification** | Claim supported: damage 'crushed_packaging' observed on 'box' in image img_1. |

### 13. User: `user_030` (Object: `package`)
**Mismatched fields:**
- **object_part**: Gold=`seal` | Pred=`box`
- **supporting_image_ids**: Gold=`img_1` | Pred=`img_1;img_2`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The first image supports the claim by showing torn-open packaging. |
| **Pred Justification** | Claim supported: damage 'broken_part' observed on 'box' in image img_1. |

### 14. User: `user_031` (Object: `package`)
**Mismatched fields:**
- **issue_type**: Gold=`water_damage` | Pred=`torn_packaging`
- **object_part**: Gold=`package_side` | Pred=`box`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image supports the water damage claim, but user history shows prior package claims often needed evidence review. |
| **Pred Justification** | Claim supported: damage 'torn_packaging' observed on 'box' in image img_1. |

### 15. User: `user_032` (Object: `package`)
**Mismatched fields:**
- **evidence_standard_met**: Gold=`false` | Pred=`true`
- **risk_flags**: Gold=`cropped_or_obstructed;damage_not_visible;manual_review_required` | Pred=`user_history_risk;manual_review_required`
- **issue_type**: Gold=`unknown` | Pred=`torn_packaging`
- **object_part**: Gold=`contents` | Pred=`box`
- **claim_status**: Gold=`not_enough_information` | Pred=`supported`
- **supporting_image_ids**: Gold=`none` | Pred=`img_1;img_2`
- **valid_image**: Gold=`false` | Pred=`true`
- **severity**: Gold=`unknown` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The package contents are unclear, so the missing-product claim cannot be verified from the submitted images. |
| **Pred Justification** | Claim supported: damage 'missing_part' observed on 'box' in image img_1. |

### 16. User: `user_033` (Object: `package`)
**Mismatched fields:**
- **evidence_standard_met**: Gold=`true` | Pred=`false`
- **risk_flags**: Gold=`wrong_object;claim_mismatch;user_history_risk;manual_review_required` | Pred=`wrong_object;user_history_risk;manual_review_required`
- **severity**: Gold=`low` | Pred=`none`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image does show a visible crease or dent, but the object shown is different from the claimed shipping box, so it does not support the user's crushed box claim. User history also shows prior severity exaggeration. |
| **Pred Justification** | Claim contradicted because submitted images show a different object, not the claimed package. |

### 17. User: `user_034` (Object: `package`)
**Mismatched fields:**
- **risk_flags**: Gold=`damage_not_visible;text_instruction_present;user_history_risk;manual_review_required` | Pred=`user_history_risk;manual_review_required`
- **issue_type**: Gold=`none` | Pred=`torn_packaging`
- **object_part**: Gold=`seal` | Pred=`box`
- **claim_status**: Gold=`contradicted` | Pred=`supported`
- **severity**: Gold=`none` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The visible package seal does not show torn-open packaging. Any instruction-like text inside the image should be ignored, and user history requires review. |
| **Pred Justification** | Claim supported: damage 'crushed_packaging' observed on 'box' in image img_1. |
