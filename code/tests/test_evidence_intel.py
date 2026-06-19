"""
Unit tests for Stage 1 & Stage 2 evidence intelligence components.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from src.models import MockAdapter, OllamaAdapter
from src.pipeline.claim_parser import parse_claim
from src.pipeline.image_quality import check_image_quality
from src.pipeline.image_reviewer import review_image
from src.schemas import ClaimInput, ParsedClaim
from src.utils.text import is_multilingual_claim


def test_is_multilingual_claim():
    # Pure English
    assert not is_multilingual_claim("The front windshield is cracked.")
    # Multilingual/Hinglish
    assert is_multilingual_claim("Windshield pe crack hai, theek kar do.")
    assert is_multilingual_claim("Mera screen tuta hua hai.")


def test_image_quality_precheck(tmp_path):
    # Test 1: Non-existent image file
    missing_path = tmp_path / "non_existent.jpg"
    assert check_image_quality(missing_path) == ["damage_not_visible"]

    # Test 2: Normal valid image file
    valid_path = tmp_path / "valid.jpg"
    img = Image.new("L", (256, 256), color=128)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    for i in range(0, 256, 16):
        draw.line([(i, 0), (i, 256)], fill=0, width=2)
        draw.line([(0, i), (256, i)], fill=255, width=2)
    img.save(valid_path)
    # Average gray image with sharp grid lines should have no flags
    assert check_image_quality(valid_path) == []

    # Test 3: Dark image (brightness < 25)
    dark_path = tmp_path / "dark.jpg"
    img_dark = Image.new("L", (100, 100), color=10)
    img_dark.save(dark_path)
    assert "low_light_or_glare" in check_image_quality(dark_path)

    # Test 4: Extremely bright/glare image (brightness > 230)
    bright_path = tmp_path / "bright.jpg"
    img_bright = Image.new("L", (100, 100), color=240)
    img_bright.save(bright_path)
    assert "low_light_or_glare" in check_image_quality(bright_path)

    # Test 5: Blurry image (using flat color, which has zero edge intensity)
    blurry_path = tmp_path / "blurry.jpg"
    img_blurry = Image.new("L", (256, 256), color=128)
    img_blurry.save(blurry_path)
    # Zero variation or edges should flag blurry_image
    assert "blurry_image" in check_image_quality(blurry_path)


def test_parse_claim():
    claim = ClaimInput(
        user_id="user_001",
        image_paths="img_1.jpg",
        user_claim="My car front bumper is dented.",
        claim_object="car",
    )
    mock_model = MockAdapter()
    parsed = parse_claim(claim, mock_model)
    
    assert isinstance(parsed, ParsedClaim)
    assert parsed.primary_object == "car"
    assert parsed.primary_part == "front_bumper"
    assert parsed.issue_hypothesis == "dent"
    assert parsed.confidence > 0.0


def test_review_image(tmp_path):
    img_path = tmp_path / "img_1.jpg"
    img = Image.new("L", (256, 256), color=128)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    for i in range(0, 256, 16):
        draw.line([(i, 0), (i, 256)], fill=0, width=2)
        draw.line([(0, i), (256, i)], fill=255, width=2)
    img.save(img_path)

    parsed_claim = ParsedClaim(
        primary_object="car",
        primary_part="door",
        issue_hypothesis="dent",
        secondary_targets=[],
        has_instruction_text=False,
        instruction_text_detail="",
        language_notes="english",
        confidence=0.9,
    )
    mock_model = MockAdapter()
    observation = review_image(img_path, parsed_claim, mock_model)
    
    assert observation.image_id == "img_1"
    assert observation.object_visible is True
    assert observation.part_seen == "door"
    assert observation.issue_observed == "dent"
    assert observation.is_usable is True


def test_ollama_adapter_unavailable():
    # Use a dummy offline port
    adapter = OllamaAdapter(base_url="http://localhost:9999", model_name="gemma4:e4b")
    assert not adapter.is_available()
    
    with pytest.raises(RuntimeError) as exc_info:
        adapter.text_call("Hello")
    
    assert "Ollama API call failed" in str(exc_info.value)
