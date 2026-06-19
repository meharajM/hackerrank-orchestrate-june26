import re
import json

def clean_and_load_json(text: str) -> dict:
    """Clean markdown response wrappers and parse JSON."""
    clean_text = text.strip()
    
    # Remove markdown code block markers
    if clean_text.startswith("```"):
        try:
            first_newline = clean_text.index("\n")
            last_fence = clean_text.rfind("```")
            if last_fence > first_newline:
                clean_text = clean_text[first_newline + 1:last_fence].strip()
        except ValueError:
            pass
            
    # Try search for the JSON object braces
    match = re.search(r"\{[\s\S]*\}", clean_text)
    if match:
        clean_text = match.group(0)
        
    return json.loads(clean_text)
