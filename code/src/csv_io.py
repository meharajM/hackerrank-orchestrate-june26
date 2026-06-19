"""
CSV I/O utilities for reading input files and writing output.csv.
Handles multiline claim transcripts safely.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

from .schemas import (
    ClaimInput,
    ClaimOutput,
    UserHistory,
    EvidenceRequirement,
    OUTPUT_COLUMNS,
)


def read_claims(csv_path: Path) -> list[ClaimInput]:
    """Read claims.csv or sample_claims.csv and return ClaimInput objects.

    Handles both input-only (4 cols) and labeled (14 cols) CSVs.
    """
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                ClaimInput(
                    user_id=row["user_id"].strip(),
                    image_paths=row["image_paths"].strip(),
                    user_claim=row["user_claim"].strip(),
                    claim_object=row["claim_object"].strip().lower(),
                )
            )
    return rows


def read_claims_with_labels(csv_path: Path) -> list[dict]:
    """Read sample_claims.csv including all output columns for evaluation."""
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize values
            cleaned = {}
            for k, v in row.items():
                cleaned[k.strip()] = v.strip() if v else ""
            rows.append(cleaned)
    return rows


def read_user_history(csv_path: Path) -> dict[str, UserHistory]:
    """Read user_history.csv and return a dict keyed by user_id."""
    history = {}
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = row["user_id"].strip()
            history[uid] = UserHistory(
                user_id=uid,
                past_claim_count=int(row["past_claim_count"]),
                accept_claim=int(row["accept_claim"]),
                manual_review_claim=int(row["manual_review_claim"]),
                rejected_claim=int(row["rejected_claim"]),
                last_90_days_claim_count=int(row["last_90_days_claim_count"]),
                history_flags=row["history_flags"].strip(),
                history_summary=row["history_summary"].strip(),
            )
    return history


def read_evidence_requirements(csv_path: Path) -> list[EvidenceRequirement]:
    """Read evidence_requirements.csv."""
    reqs = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            reqs.append(
                EvidenceRequirement(
                    requirement_id=row["requirement_id"].strip(),
                    claim_object=row["claim_object"].strip(),
                    applies_to=row["applies_to"].strip(),
                    minimum_image_evidence=row["minimum_image_evidence"].strip(),
                )
            )
    return reqs


def write_output(rows: list[ClaimOutput], output_path: Path) -> None:
    """Write output.csv with exact column order from problem_statement.md."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=OUTPUT_COLUMNS,
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_row_dict())


def get_evidence_requirements_for_claim(
    requirements: list[EvidenceRequirement],
    claim_object: str,
    issue_family: Optional[str] = None,
) -> list[EvidenceRequirement]:
    """Filter evidence requirements relevant to a specific claim."""
    relevant = []
    for req in requirements:
        if req.claim_object in ("all", claim_object):
            if issue_family is None:
                relevant.append(req)
            else:
                # Fuzzy match on applies_to
                applies = req.applies_to.lower()
                if issue_family.lower() in applies or applies in issue_family.lower():
                    relevant.append(req)
                elif req.claim_object == "all":
                    relevant.append(req)
    return relevant
