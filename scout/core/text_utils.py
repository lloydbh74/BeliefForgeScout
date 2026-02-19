import re

def normalize_whitespace(text: str) -> str:
    """
    Replaces non-standard whitespace characters (NBSP, thin spaces, etc.)
    with standard keyboard spaces (\u0020). Preserves newlines.
    """
    if not text:
        return ""
    
    # [^\S\r\n] matches any whitespace character except carriage return and newline.
    # We replace each individual non-standard space with a standard one.
    return re.sub(r'[^\S\r\n]', ' ', text)
