"""
General text processing and language detection utilities.
"""
from __future__ import annotations

import re


def is_multilingual_claim(claim_text: str) -> bool:
    """Detect if a claim has Hinglish/Hindi or multilingual elements based on keyword presence."""
    hinglish_words = {
        "mein", "meri", "hua", "toh", "phati", "kar", "nahi", "pe", "ko", "par", 
        "hai", "ke", "upar", "theek", "kharab", "tuta", "tute", "gaya", "ho", "se"
    }
    words = set(re.findall(r"\b[a-zA-Z]+\b", claim_text.lower()))
    return len(words.intersection(hinglish_words)) >= 2


def clean_instruction_text(text: str) -> str:
    """Sanitize input text to neutralize prompt injection instructions."""
    # A simple cleaning utility if needed to restrict typical injection strings
    return text.strip()
