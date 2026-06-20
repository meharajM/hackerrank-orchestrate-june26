import json
import re


def clean_and_load_json(text: str) -> dict:
    """Clean markdown response wrappers and parse JSON."""
    clean_text = _strip_response_wrappers(text.strip())

    match = re.search(r"\{[\s\S]*\}", clean_text)
    if match:
        clean_text = match.group(0)

    for candidate in _json_repair_candidates(clean_text):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    raise json.JSONDecodeError("Unable to parse model JSON response", clean_text, 0)


def _json_repair_candidates(text: str) -> list[str]:
    common = _repair_common_json_issues(text)
    escaped = _repair_invalid_escapes(text)
    escaped_common = _repair_invalid_escapes(common)
    return [text, common, escaped, escaped_common]


def _strip_response_wrappers(text: str) -> str:
    """Remove markdown fences and common reasoning wrappers from model output."""
    clean_text = text
    if clean_text.startswith("```"):
        try:
            first_newline = clean_text.index("\n")
            last_fence = clean_text.rfind("```")
            if last_fence > first_newline:
                clean_text = clean_text[first_newline + 1:last_fence].strip()
        except ValueError:
            pass

    clean_text = _strip_think_tags(clean_text, "<think>", "</think>")

    tick = chr(96)
    clean_text = _strip_think_tags(clean_text, f"{tick}think{tick}", f"{tick}/think{tick}")

    return clean_text.strip()


def _strip_think_tags(text: str, open_tag: str, close_tag: str) -> str:
    """Strip all occurrences of open_tag...close_tag blocks from text."""
    result = text
    while open_tag in result:
        start = result.find(open_tag)
        end = result.find(close_tag, start)
        if end == -1:
            result = result[:start]
            break
        result = result[:start] + result[end + len(close_tag):]
    return result


def _repair_common_json_issues(text: str) -> str:
    """Repair common model JSON mistakes without changing the object structure."""
    repaired = text
    repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)
    repaired = repaired.replace("\r\n", "\n")
    return repaired


def _repair_invalid_escapes(text: str) -> str:
    """Escape backslashes that are not valid JSON escape sequences."""
    repaired = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", text)
    # Preserve literal backslash-n sequences such as "\new" instead of newline.
    repaired = re.sub(r'\\n(?=[A-Za-z])', r"\\\\n", repaired)
    return repaired
