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

    def text_call(self, prompt: str, system_prompt: str = "") -> str:
        """Mock text call."""
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
        
        # Determine object
        claim_object = "car"
        if "laptop" in prompt_lower:
            claim_object = "laptop"
        elif "package" in prompt_lower:
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
            if "bumper" in prompt_lower:
                object_part = "front_bumper"
            if "scratch" in prompt_lower:
                issue_type = "scratch"
        elif claim_object == "laptop":
            object_part = "screen"
            issue_type = "crack"
            if "keyboard" in prompt_lower:
                object_part = "keyboard"
        elif claim_object == "package":
            object_part = "box"
            issue_type = "torn_packaging"
            if "crushed" in prompt_lower:
                issue_type = "crushed_packaging"

        # Simulate instruction text flag check
        if "approve" in prompt_lower or "ignore rules" in prompt_lower:
            risk_flags = ["text_instruction_present"]

        # If user history risk is mentioned in the prompt, pass it along
        if "user_history_risk" in prompt_lower:
            risk_flags.append("user_history_risk")

        response_data = {
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
