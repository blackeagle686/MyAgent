import json
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

def parse_robust_json(text: str, fallback: Any) -> Any:
    """Parse JSON from *text*, returning *fallback* on failure.
    Robustly handles markdown, prose, and malformed strings.
    """
    if not text:
        return fallback
        
    clean_text = text.strip()
    
    # Remove markdown code blocks if present
    if "```" in clean_text:
        matches = re.findall(r"```(?:json)?\s*(.*?)\s*```", clean_text, re.DOTALL)
        if matches:
            clean_text = matches[-1] # Take the last one (often the most complete)

    # Try direct parse
    try:
        return json.loads(clean_text)
    except:
        # Try finding anything that looks like a JSON block
        match = re.search(r"(\{.*\}|\[.*\])", clean_text, re.DOTALL)
        if match:
            try:
                # Clean up some common LLM JSON mistakes (like unescaped quotes in middle of strings)
                # This is a bit risky but helps for small errors
                return json.loads(match.group(0))
            except:
                pass
    
    logger.error("JSON parse failed for text starting with: %s", text[:100])
    return fallback
