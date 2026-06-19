# Evaluation Report — Damage Claim Verification System

## Metadata
- **Strategy Name:** csv_import
- **Model/Adapter:** strategy_b_predictions.csv
- **Total Claims Evaluated:** 20

## Headline Summary
| Metric | Score | Matches | Details |
|---|---|---|---|
| **Row Exact Match** | **0.0%** | 0/20 | Decided over all 8 core decision fields |
| **Risk Flags F1-Score** | **25.2%** | - | Precision: 0.26, Recall: 0.75 |
| **Supporting Images F1-Score** | **80.0%** | - | Precision: 0.75, Recall: 1.00 |

## Per-Field Accuracy
| Field Name | Accuracy | Correct |
|---|---|---|
| `valid_image` | 90.0% | 18/20 |
| `evidence_standard_met` | 80.0% | 16/20 |
| `claim_status` | 65.0% | 13/20 |
| `supporting_image_ids` | 60.0% | 12/20 |
| `severity` | 55.0% | 11/20 |
| `issue_type` | 35.0% | 7/20 |
| `object_part` | 25.0% | 5/20 |
| `risk_flags` | 0.0% | 0/20 |

## Slice Analysis
| Slice Category | Group | Count | Exact Match | Risk Flags F1 | Supporting Images F1 |
|---|---|---|---|---|---|
| **Claim Object** | | | | | |
| - | Car | 8 | 0.0% | 20.5% | 75.0% |
| - | Laptop | 6 | 0.0% | 11.1% | 88.9% |
| - | Package | 6 | 0.0% | 45.7% | 77.8% |
| **Image Count** | | | | | |
| - | 1 Image | 11 | 0.0% | 25.3% | 90.9% |
| - | 2+ Images | 9 | 0.0% | 25.1% | 66.7% |
| **Claim Status (Gold)** | | | | | |
| - | Supported | 12 | 0.0% | 6.7% | 86.1% |
| - | Contradicted | 5 | 0.0% | 70.2% | 93.3% |
| - | Not Enough Info | 3 | 0.0% | 24.4% | 33.3% |
| **History Risk (Gold)** | | | | | |
| - | Has Risk Flag | 6 | 0.0% | 71.9% | 94.4% |
| - | No Risk Flag | 14 | 0.0% | 5.2% | 73.8% |
| **Language Status** | | | | | |
| - | Multilingual (Hinglish) | 2 | 0.0% | 20.0% | 83.3% |
| - | English | 18 | 0.0% | 25.8% | 79.6% |

## Error Details / Mismatches
Found 20 mismatched row(s). Details below:

### 1. User: `user_001` (Object: `car`)
**Mismatched fields:**
- **risk_flags**: Gold=`none` | Pred=`text_instruction_present;manual_review_required`
- **object_part**: Gold=`rear_bumper` | Pred=`front_bumper`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image clearly shows a dent on the rear bumper and the user history does not add risk. |
| **Pred Justification** | Claim supported: damage 'dent' observed on 'front_bumper' in image img_1. |

### 2. User: `user_002` (Object: `car`)
**Mismatched fields:**
- **evidence_standard_met**: Gold=`false` | Pred=`true`
- **risk_flags**: Gold=`wrong_object;claim_mismatch;manual_review_required` | Pred=`text_instruction_present;manual_review_required`
- **issue_type**: Gold=`broken_part` | Pred=`scratch`
- **claim_status**: Gold=`not_enough_information` | Pred=`supported`
- **severity**: Gold=`unknown` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The submitted images do not reliably support the claim because the damaged close-up and the full vehicle view appear to be from different cars. |
| **Pred Justification** | Claim supported: damage 'scratch' observed on 'front_bumper' in image img_1. |

### 3. User: `user_004` (Object: `car`)
**Mismatched fields:**
- **risk_flags**: Gold=`none` | Pred=`text_instruction_present;manual_review_required`
- **issue_type**: Gold=`crack` | Pred=`dent`
- **object_part**: Gold=`windshield` | Pred=`door`
- **supporting_image_ids**: Gold=`img_1` | Pred=`img_1;img_2`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image set supports the claim because the windshield crack is visible in the close-up. |
| **Pred Justification** | Claim supported: damage 'dent' observed on 'door' in image img_1. |

### 4. User: `user_007` (Object: `car`)
**Mismatched fields:**
- **risk_flags**: Gold=`none` | Pred=`text_instruction_present;manual_review_required`
- **issue_type**: Gold=`broken_part` | Pred=`dent`
- **object_part**: Gold=`side_mirror` | Pred=`door`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The submitted image directly shows damage to the claimed side mirror. |
| **Pred Justification** | Claim supported: damage 'dent' observed on 'door' in image img_1. |

### 5. User: `user_005` (Object: `car`)
**Mismatched fields:**
- **risk_flags**: Gold=`claim_mismatch;user_history_risk;manual_review_required` | Pred=`text_instruction_present;user_history_risk;manual_review_required`
- **issue_type**: Gold=`scratch` | Pred=`dent`
- **object_part**: Gold=`rear_bumper` | Pred=`front_bumper`
- **claim_status**: Gold=`contradicted` | Pred=`supported`
- **supporting_image_ids**: Gold=`img_1` | Pred=`img_1;img_2`
- **severity**: Gold=`low` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The images show only minor rear bumper scratching, so the severe damage claim is contradicted. User history also shows several rejected claims. |
| **Pred Justification** | Claim supported: damage 'dent' observed on 'front_bumper' in image img_1. |

### 6. User: `user_006` (Object: `car`)
**Mismatched fields:**
- **evidence_standard_met**: Gold=`false` | Pred=`true`
- **risk_flags**: Gold=`wrong_angle;damage_not_visible` | Pred=`text_instruction_present;manual_review_required`
- **issue_type**: Gold=`unknown` | Pred=`dent`
- **object_part**: Gold=`headlight` | Pred=`door`
- **claim_status**: Gold=`not_enough_information` | Pred=`supported`
- **supporting_image_ids**: Gold=`none` | Pred=`img_1`
- **severity**: Gold=`unknown` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The submitted image shows another part of the car and does not provide evidence for the headlight claim. |
| **Pred Justification** | Claim supported: damage 'dent' observed on 'door' in image img_1. |

### 7. User: `user_003` (Object: `car`)
**Mismatched fields:**
- **risk_flags**: Gold=`blurry_image` | Pred=`text_instruction_present;manual_review_required`
- **supporting_image_ids**: Gold=`img_2` | Pred=`img_1;img_2`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The clearer second image supports the claim by showing a dent on the door. |
| **Pred Justification** | Claim supported: damage 'dent' observed on 'door' in image img_1. |

### 8. User: `user_008` (Object: `car`)
**Mismatched fields:**
- **risk_flags**: Gold=`claim_mismatch;non_original_image;user_history_risk;manual_review_required` | Pred=`text_instruction_present;user_history_risk;manual_review_required`
- **issue_type**: Gold=`broken_part` | Pred=`scratch`
- **object_part**: Gold=`front_bumper` | Pred=`door`
- **claim_status**: Gold=`contradicted` | Pred=`supported`
- **valid_image**: Gold=`false` | Pred=`true`
- **severity**: Gold=`high` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image shows severe front-end damage rather than a scratch on the hood, so it does not support the user's hood-scratch claim. |
| **Pred Justification** | Claim supported: damage 'scratch' observed on 'door' in image img_1. |

### 9. User: `user_009` (Object: `laptop`)
**Mismatched fields:**
- **risk_flags**: Gold=`none` | Pred=`text_instruction_present;manual_review_required`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image directly shows a crack on the laptop screen. |
| **Pred Justification** | Claim supported: damage 'crack' observed on 'screen' in image img_1. |

### 10. User: `user_010` (Object: `laptop`)
**Mismatched fields:**
- **risk_flags**: Gold=`none` | Pred=`text_instruction_present;manual_review_required`
- **issue_type**: Gold=`broken_part` | Pred=`crack`
- **object_part**: Gold=`hinge` | Pred=`screen`
- **supporting_image_ids**: Gold=`img_1` | Pred=`img_1;img_2`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The first image supports the claim because the hinge damage is visible. |
| **Pred Justification** | Claim supported: damage 'crack' observed on 'screen' in image img_1. |

### 11. User: `user_011` (Object: `laptop`)
**Mismatched fields:**
- **risk_flags**: Gold=`none` | Pred=`text_instruction_present;manual_review_required`
- **issue_type**: Gold=`stain` | Pred=`crack`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The submitted image shows visible staining on the keyboard area. |
| **Pred Justification** | Claim supported: damage 'crack' observed on 'keyboard' in image img_1. |

### 12. User: `user_012` (Object: `laptop`)
**Mismatched fields:**
- **risk_flags**: Gold=`none` | Pred=`text_instruction_present;manual_review_required`
- **issue_type**: Gold=`dent` | Pred=`crack`
- **object_part**: Gold=`corner` | Pred=`screen`
- **supporting_image_ids**: Gold=`img_2` | Pred=`img_1;img_2`
- **severity**: Gold=`low` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image set supports the claim because the corner dent is visible in the close-up. |
| **Pred Justification** | Claim supported: damage 'crack' observed on 'screen' in image img_1. |

### 13. User: `user_018` (Object: `laptop`)
**Mismatched fields:**
- **risk_flags**: Gold=`none` | Pred=`text_instruction_present;manual_review_required`
- **object_part**: Gold=`screen` | Pred=`keyboard`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image supports the claim because the laptop screen has visible cracking consistent with the user's screen damage report. |
| **Pred Justification** | Claim supported: damage 'crack' observed on 'keyboard' in image img_1. |

### 14. User: `user_020` (Object: `laptop`)
**Mismatched fields:**
- **risk_flags**: Gold=`damage_not_visible;user_history_risk;manual_review_required` | Pred=`text_instruction_present;user_history_risk;manual_review_required`
- **issue_type**: Gold=`none` | Pred=`crack`
- **object_part**: Gold=`trackpad` | Pred=`screen`
- **claim_status**: Gold=`contradicted` | Pred=`supported`
- **severity**: Gold=`none` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image shows the trackpad area but does not show clear physical damage, so it contradicts the user's physical damage claim. The user's prior claim history also requires review. |
| **Pred Justification** | Claim supported: damage 'crack' observed on 'screen' in image img_1. |

### 15. User: `user_015` (Object: `package`)
**Mismatched fields:**
- **risk_flags**: Gold=`none` | Pred=`text_instruction_present;manual_review_required`
- **object_part**: Gold=`package_corner` | Pred=`box`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image directly shows crushing on the claimed package corner. |
| **Pred Justification** | Claim supported: damage 'crushed_packaging' observed on 'box' in image img_1. |

### 16. User: `user_030` (Object: `package`)
**Mismatched fields:**
- **risk_flags**: Gold=`none` | Pred=`text_instruction_present;manual_review_required`
- **object_part**: Gold=`seal` | Pred=`box`
- **supporting_image_ids**: Gold=`img_1` | Pred=`img_1;img_2`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The first image supports the claim by showing torn-open packaging. |
| **Pred Justification** | Claim supported: damage 'torn_packaging' observed on 'box' in image img_1. |

### 17. User: `user_031` (Object: `package`)
**Mismatched fields:**
- **risk_flags**: Gold=`user_history_risk;manual_review_required` | Pred=`text_instruction_present;user_history_risk;manual_review_required`
- **issue_type**: Gold=`water_damage` | Pred=`torn_packaging`
- **object_part**: Gold=`package_side` | Pred=`box`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image supports the water damage claim, but user history shows prior package claims often needed evidence review. |
| **Pred Justification** | Claim supported: damage 'torn_packaging' observed on 'box' in image img_1. |

### 18. User: `user_032` (Object: `package`)
**Mismatched fields:**
- **evidence_standard_met**: Gold=`false` | Pred=`true`
- **risk_flags**: Gold=`cropped_or_obstructed;damage_not_visible;manual_review_required` | Pred=`text_instruction_present;user_history_risk;manual_review_required`
- **issue_type**: Gold=`unknown` | Pred=`torn_packaging`
- **object_part**: Gold=`contents` | Pred=`box`
- **claim_status**: Gold=`not_enough_information` | Pred=`supported`
- **supporting_image_ids**: Gold=`none` | Pred=`img_1;img_2`
- **valid_image**: Gold=`false` | Pred=`true`
- **severity**: Gold=`unknown` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The package contents are unclear, so the missing-product claim cannot be verified from the submitted images. |
| **Pred Justification** | Claim supported: damage 'torn_packaging' observed on 'box' in image img_1. |

### 19. User: `user_033` (Object: `package`)
**Mismatched fields:**
- **evidence_standard_met**: Gold=`true` | Pred=`false`
- **risk_flags**: Gold=`wrong_object;claim_mismatch;user_history_risk;manual_review_required` | Pred=`wrong_object;text_instruction_present;user_history_risk;manual_review_required`
- **severity**: Gold=`low` | Pred=`none`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image does show a visible crease or dent, but the object shown is different from the claimed shipping box, so it does not support the user's crushed box claim. User history also shows prior severity exaggeration. |
| **Pred Justification** | Claim contradicted because submitted images show a different object, not the claimed package. |

### 20. User: `user_034` (Object: `package`)
**Mismatched fields:**
- **risk_flags**: Gold=`damage_not_visible;text_instruction_present;user_history_risk;manual_review_required` | Pred=`text_instruction_present;user_history_risk;manual_review_required`
- **issue_type**: Gold=`none` | Pred=`crushed_packaging`
- **object_part**: Gold=`seal` | Pred=`box`
- **claim_status**: Gold=`contradicted` | Pred=`supported`
- **severity**: Gold=`none` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The visible package seal does not show torn-open packaging. Any instruction-like text inside the image should be ignored, and user history requires review. |
| **Pred Justification** | Claim supported: damage 'crushed_packaging' observed on 'box' in image img_1. |
