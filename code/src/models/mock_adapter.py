"""
Mock model adapter for testing and offline development.
Returns deterministic, schema-valid JSON responses.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .base import ModelAdapter


class MockAdapter(ModelAdapter):
    """Mock adapter that returns realistic schema-valid JSON mock responses."""

    def __init__(self, name: str = "MockAdapter"):
        self._name = name
        self.last_prompt = ""
        self.last_system_prompt = ""
        self.last_image_paths = []
        self._call_count = 0

    def get_stats(self) -> dict:
        return {
            "call_count": self._call_count,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
        }

    def text_call(self, prompt: str, system_prompt: str = "") -> str:
        """Mock text call."""
        self._call_count += 1
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt
        return self._generate_mock_response(prompt)

    def multimodal_call(
        self,
        prompt: str,
        image_paths: list[Path],
        system_prompt: str = "",
    ) -> str:
        """Mock multimodal call."""
        self._call_count += 1
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt
        self.last_image_paths = image_paths
        return self._generate_mock_response(prompt)

    def is_available(self) -> bool:
        """Mock adapter is always available."""
        return True

    @property
    def name(self) -> str:
        return self._name

    def _generate_mock_response(self, prompt: str) -> str:
        """Generate a realistic mock JSON response by parsing the prompt for clues."""
        # Simple heuristics based on prompt
        prompt_lower = prompt.lower()
        
        # Isolate the input/context portion of the prompt to avoid matching the system instructions allowed enums
        input_text = prompt_lower
        if "### input text:" in prompt_lower:
            parts = prompt_lower.split("### input text:")
            if len(parts) > 1:
                input_text = parts[1].split("###")[0].strip()
        elif "### claim context:" in prompt_lower:
            parts = prompt_lower.split("### claim context:")
            if len(parts) > 1:
                input_text = parts[1].split("###")[0].strip()
        
        # Determine object
        claim_object = "car"
        if "laptop" in input_text:
            claim_object = "laptop"
        elif "package" in input_text:
            claim_object = "package"

        # Determine part and issue
        object_part = "unknown"
        issue_type = "unknown"
        severity = "medium"
        claim_status = "supported"
        supporting_image_ids = ["img_1"]
        risk_flags = ["none"]

        if claim_object == "car":
            object_part = "door"
            issue_type = "dent"
            if "bumper" in input_text:
                object_part = "front_bumper"
            if "scratch" in input_text:
                issue_type = "scratch"
        elif claim_object == "laptop":
            object_part = "screen"
            issue_type = "crack"
            if "keyboard" in input_text:
                object_part = "keyboard"
        elif claim_object == "package":
            object_part = "box"
            issue_type = "torn_packaging"
            if "crushed" in input_text:
                issue_type = "crushed_packaging"

        # Simulate instruction text flag check
        if "approve" in prompt_lower or "ignore rules" in prompt_lower:
            risk_flags = ["text_instruction_present"]

        # If user history risk is mentioned in the prompt, pass it along
        if "user_history_risk" in prompt_lower:
            risk_flags.append("user_history_risk")

        response_data = {
            # Stage 1 ParsedClaim fields
            "primary_object": claim_object,
            "primary_part": object_part,
            "issue_hypothesis": issue_type,
            "secondary_targets": [],
            "has_instruction_text": "text_instruction_present" in risk_flags,
            "instruction_text_detail": "Instruction text detected" if "text_instruction_present" in risk_flags else "",
            "language_notes": "english",
            "confidence": 0.95,
            
            # Stage 2 ImageObservation fields
            "image_id": "img_1",
            "object_visible": True,
            "object_type_seen": claim_object,
            "relevant_part_visible": True,
            "part_seen": object_part,
            "issue_observed": issue_type,
            "issue_matches_claim": True,
            "severity_estimate": severity,
            "quality_issues": risk_flags,
            "is_usable": True,
            "mismatch_notes": "",
            "has_text_instruction": "text_instruction_present" in risk_flags,
            "authenticity_concern": False,
            "raw_description": f"A clear image showing the {object_part} of the {claim_object}.",

            # Final ClaimOutput fields (for compatibility)
            "evidence_standard_met": True,
            "evidence_standard_met_reason": "Visual evidence matches the claimed object and part.",
            "risk_flags": risk_flags,
            "issue_type": issue_type,
            "object_part": object_part,
            "claim_status": claim_status,
            "claim_status_justification": f"The submitted images clearly show the claimed {issue_type} on the {object_part} of the {claim_object}.",
            "supporting_image_ids": supporting_image_ids,
            "valid_image": True,
            "severity": severity
        }

        return json.dumps(response_data)
