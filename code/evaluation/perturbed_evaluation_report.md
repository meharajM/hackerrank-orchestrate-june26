# Evaluation Report — Damage Claim Verification System

## Metadata
- **Strategy Name:** csv_import
- **Model/Adapter:** perturbed_predictions.csv
- **Total Claims Evaluated:** 20

## Headline Summary
| Metric | Score | Matches | Details |
|---|---|---|---|
| **Row Exact Match** | **0.0%** | 0/20 | Decided over all 8 core decision fields |
| **Risk Flags F1-Score** | **66.8%** | - | Precision: 1.00, Recall: 0.61 |
| **Supporting Images F1-Score** | **76.7%** | - | Precision: 0.80, Recall: 0.85 |

## Per-Field Accuracy
| Field Name | Accuracy | Correct |
|---|---|---|
| `evidence_standard_met` | 85.0% | 17/20 |
| `valid_image` | 85.0% | 17/20 |
| `supporting_image_ids` | 70.0% | 14/20 |
| `claim_status` | 55.0% | 11/20 |
| `severity` | 55.0% | 11/20 |
| `risk_flags` | 50.0% | 10/20 |
| `issue_type` | 20.0% | 4/20 |
| `object_part` | 15.0% | 3/20 |

## Slice Analysis
| Slice Category | Group | Count | Exact Match | Risk Flags F1 | Supporting Images F1 |
|---|---|---|---|---|---|
| **Claim Object** | | | | | |
| - | Car | 8 | 0.0% | 48.8% | 70.8% |
| - | Laptop | 6 | 0.0% | 91.7% | 83.3% |
| - | Package | 6 | 0.0% | 66.1% | 77.8% |
| **Image Count** | | | | | |
| - | 1 Image | 11 | 0.0% | 72.4% | 90.9% |
| - | 2+ Images | 9 | 0.0% | 60.0% | 59.3% |
| **Claim Status (Gold)** | | | | | |
| - | Supported | 12 | 0.0% | 88.9% | 83.3% |
| - | Contradicted | 5 | 0.0% | 44.0% | 93.3% |
| - | Not Enough Info | 3 | 0.0% | 16.7% | 22.2% |
| **History Risk (Gold)** | | | | | |
| - | Has Risk Flag | 6 | 0.0% | 47.8% | 94.4% |
| - | No Risk Flag | 14 | 0.0% | 75.0% | 69.0% |
| **Language Status** | | | | | |
| - | Multilingual (Hinglish) | 2 | 0.0% | 50.0% | 83.3% |
| - | English | 18 | 0.0% | 68.7% | 75.9% |

## Error Details / Mismatches
Found 20 mismatched row(s). Details below:

### 1. User: `user_001` (Object: `car`)
**Mismatched fields:**
- **issue_type**: Gold=`dent` | Pred=`scratch`
- **object_part**: Gold=`rear_bumper` | Pred=`front_bumper`
- **claim_status**: Gold=`supported` | Pred=`contradicted`
- **valid_image**: Gold=`true` | Pred=`false`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image clearly shows a dent on the rear bumper and the user history does not add risk. |
| **Pred Justification** | The submitted images clearly show the claimed scratch on the front_bumper of the car. |

### 2. User: `user_002` (Object: `car`)
**Mismatched fields:**
- **evidence_standard_met**: Gold=`false` | Pred=`true`
- **risk_flags**: Gold=`wrong_object;claim_mismatch;manual_review_required` | Pred=`none`
- **issue_type**: Gold=`broken_part` | Pred=`scratch`
- **claim_status**: Gold=`not_enough_information` | Pred=`supported`
- **supporting_image_ids**: Gold=`img_1;img_2` | Pred=`img_1`
- **severity**: Gold=`unknown` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The submitted images do not reliably support the claim because the damaged close-up and the full vehicle view appear to be from different cars. |
| **Pred Justification** | The submitted images clearly show the claimed scratch on the front_bumper of the car. |

### 3. User: `user_004` (Object: `car`)
**Mismatched fields:**
- **issue_type**: Gold=`crack` | Pred=`scratch`
- **object_part**: Gold=`windshield` | Pred=`front_bumper`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image set supports the claim because the windshield crack is visible in the close-up. |
| **Pred Justification** | The submitted images clearly show the claimed scratch on the front_bumper of the car. |

### 4. User: `user_007` (Object: `car`)
**Mismatched fields:**
- **issue_type**: Gold=`broken_part` | Pred=`scratch`
- **object_part**: Gold=`side_mirror` | Pred=`front_bumper`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The submitted image directly shows damage to the claimed side mirror. |
| **Pred Justification** | The submitted images clearly show the claimed scratch on the front_bumper of the car. |

### 5. User: `user_005` (Object: `car`)
**Mismatched fields:**
- **risk_flags**: Gold=`claim_mismatch;user_history_risk;manual_review_required` | Pred=`user_history_risk`
- **object_part**: Gold=`rear_bumper` | Pred=`front_bumper`
- **claim_status**: Gold=`contradicted` | Pred=`supported`
- **severity**: Gold=`low` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The images show only minor rear bumper scratching, so the severe damage claim is contradicted. User history also shows several rejected claims. |
| **Pred Justification** | The submitted images clearly show the claimed scratch on the front_bumper of the car. |

### 6. User: `user_006` (Object: `car`)
**Mismatched fields:**
- **evidence_standard_met**: Gold=`false` | Pred=`true`
- **risk_flags**: Gold=`wrong_angle;damage_not_visible` | Pred=`none`
- **issue_type**: Gold=`unknown` | Pred=`scratch`
- **object_part**: Gold=`headlight` | Pred=`front_bumper`
- **claim_status**: Gold=`not_enough_information` | Pred=`supported`
- **supporting_image_ids**: Gold=`none` | Pred=`img_1`
- **severity**: Gold=`unknown` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The submitted image shows another part of the car and does not provide evidence for the headlight claim. |
| **Pred Justification** | The submitted images clearly show the claimed scratch on the front_bumper of the car. |

### 7. User: `user_003` (Object: `car`)
**Mismatched fields:**
- **risk_flags**: Gold=`blurry_image` | Pred=`none`
- **issue_type**: Gold=`dent` | Pred=`scratch`
- **object_part**: Gold=`door` | Pred=`front_bumper`
- **supporting_image_ids**: Gold=`img_2` | Pred=`img_1`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The clearer second image supports the claim by showing a dent on the door. |
| **Pred Justification** | The submitted images clearly show the claimed scratch on the front_bumper of the car. |

### 8. User: `user_008` (Object: `car`)
**Mismatched fields:**
- **risk_flags**: Gold=`claim_mismatch;non_original_image;user_history_risk;manual_review_required` | Pred=`user_history_risk`
- **issue_type**: Gold=`broken_part` | Pred=`scratch`
- **claim_status**: Gold=`contradicted` | Pred=`supported`
- **valid_image**: Gold=`false` | Pred=`true`
- **severity**: Gold=`high` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image shows severe front-end damage rather than a scratch on the hood, so it does not support the user's hood-scratch claim. |
| **Pred Justification** | The submitted images clearly show the claimed scratch on the front_bumper of the car. |

### 9. User: `user_009` (Object: `laptop`)
**Mismatched fields:**
- **object_part**: Gold=`screen` | Pred=`keyboard`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image directly shows a crack on the laptop screen. |
| **Pred Justification** | The submitted images clearly show the claimed crack on the keyboard of the laptop. |

### 10. User: `user_010` (Object: `laptop`)
**Mismatched fields:**
- **issue_type**: Gold=`broken_part` | Pred=`crack`
- **object_part**: Gold=`hinge` | Pred=`keyboard`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The first image supports the claim because the hinge damage is visible. |
| **Pred Justification** | The submitted images clearly show the claimed crack on the keyboard of the laptop. |

### 11. User: `user_011` (Object: `laptop`)
**Mismatched fields:**
- **issue_type**: Gold=`stain` | Pred=`crack`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The submitted image shows visible staining on the keyboard area. |
| **Pred Justification** | The submitted images clearly show the claimed crack on the keyboard of the laptop. |

### 12. User: `user_012` (Object: `laptop`)
**Mismatched fields:**
- **issue_type**: Gold=`dent` | Pred=`crack`
- **object_part**: Gold=`corner` | Pred=`keyboard`
- **supporting_image_ids**: Gold=`img_2` | Pred=`img_1`
- **severity**: Gold=`low` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image set supports the claim because the corner dent is visible in the close-up. |
| **Pred Justification** | The submitted images clearly show the claimed crack on the keyboard of the laptop. |

### 13. User: `user_018` (Object: `laptop`)
**Mismatched fields:**
- **object_part**: Gold=`screen` | Pred=`keyboard`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image supports the claim because the laptop screen has visible cracking consistent with the user's screen damage report. |
| **Pred Justification** | The submitted images clearly show the claimed crack on the keyboard of the laptop. |

### 14. User: `user_020` (Object: `laptop`)
**Mismatched fields:**
- **risk_flags**: Gold=`damage_not_visible;user_history_risk;manual_review_required` | Pred=`user_history_risk`
- **issue_type**: Gold=`none` | Pred=`crack`
- **object_part**: Gold=`trackpad` | Pred=`keyboard`
- **claim_status**: Gold=`contradicted` | Pred=`supported`
- **severity**: Gold=`none` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image shows the trackpad area but does not show clear physical damage, so it contradicts the user's physical damage claim. The user's prior claim history also requires review. |
| **Pred Justification** | The submitted images clearly show the claimed crack on the keyboard of the laptop. |

### 15. User: `user_015` (Object: `package`)
**Mismatched fields:**
- **object_part**: Gold=`package_corner` | Pred=`box`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image directly shows crushing on the claimed package corner. |
| **Pred Justification** | The submitted images clearly show the claimed crushed_packaging on the box of the package. |

### 16. User: `user_030` (Object: `package`)
**Mismatched fields:**
- **issue_type**: Gold=`torn_packaging` | Pred=`crushed_packaging`
- **object_part**: Gold=`seal` | Pred=`box`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The first image supports the claim by showing torn-open packaging. |
| **Pred Justification** | The submitted images clearly show the claimed crushed_packaging on the box of the package. |

### 17. User: `user_031` (Object: `package`)
**Mismatched fields:**
- **risk_flags**: Gold=`user_history_risk;manual_review_required` | Pred=`user_history_risk`
- **issue_type**: Gold=`water_damage` | Pred=`crushed_packaging`
- **object_part**: Gold=`package_side` | Pred=`box`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image supports the water damage claim, but user history shows prior package claims often needed evidence review. |
| **Pred Justification** | The submitted images clearly show the claimed crushed_packaging on the box of the package. |

### 18. User: `user_032` (Object: `package`)
**Mismatched fields:**
- **evidence_standard_met**: Gold=`false` | Pred=`true`
- **risk_flags**: Gold=`cropped_or_obstructed;damage_not_visible;manual_review_required` | Pred=`manual_review_required`
- **issue_type**: Gold=`unknown` | Pred=`crushed_packaging`
- **object_part**: Gold=`contents` | Pred=`box`
- **claim_status**: Gold=`not_enough_information` | Pred=`supported`
- **supporting_image_ids**: Gold=`none` | Pred=`img_1`
- **valid_image**: Gold=`false` | Pred=`true`
- **severity**: Gold=`unknown` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The package contents are unclear, so the missing-product claim cannot be verified from the submitted images. |
| **Pred Justification** | The submitted images clearly show the claimed crushed_packaging on the box of the package. |

### 19. User: `user_033` (Object: `package`)
**Mismatched fields:**
- **risk_flags**: Gold=`wrong_object;claim_mismatch;user_history_risk;manual_review_required` | Pred=`user_history_risk`
- **issue_type**: Gold=`unknown` | Pred=`crushed_packaging`
- **object_part**: Gold=`unknown` | Pred=`box`
- **claim_status**: Gold=`contradicted` | Pred=`supported`
- **severity**: Gold=`low` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The image does show a visible crease or dent, but the object shown is different from the claimed shipping box, so it does not support the user's crushed box claim. User history also shows prior severity exaggeration. |
| **Pred Justification** | The submitted images clearly show the claimed crushed_packaging on the box of the package. |

### 20. User: `user_034` (Object: `package`)
**Mismatched fields:**
- **risk_flags**: Gold=`damage_not_visible;text_instruction_present;user_history_risk;manual_review_required` | Pred=`user_history_risk`
- **issue_type**: Gold=`none` | Pred=`crushed_packaging`
- **object_part**: Gold=`seal` | Pred=`box`
- **claim_status**: Gold=`contradicted` | Pred=`supported`
- **supporting_image_ids**: Gold=`img_1;img_2` | Pred=`img_1`
- **severity**: Gold=`none` | Pred=`medium`

| Justification Source | Text |
|---|---|
| **Gold Justification** | The visible package seal does not show torn-open packaging. Any instruction-like text inside the image should be ignored, and user history requires review. |
| **Pred Justification** | The submitted images clearly show the claimed crushed_packaging on the box of the package. |
