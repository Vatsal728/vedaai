import re
from typing import Optional, Tuple

def normalize_label(raw: Optional[str]) -> Optional[str]:
    """
    Normalize detected label to canonical form: "11-a" or "2" or "11"
    Handles: "Q1", "Q. 2", "11(a)", "11 a", "11. a.", "Q11B" -> "11-b"
    """
    if not raw:
        return None
    s = raw.strip().lower()
    # remove prefixes
    s = re.sub(r'^(q\.?|question|ans\.?|answer)\s*', '', s)
    s = s.strip()
    # handle like "11(a)" or "11 a" or "11. a"
    m = re.match(r'^(\d+)\s*[\(\.\-]?\s*([a-z])\s*[\)\.]?\s*$', s)
    if m:
        num, sub = m.groups()
        return f"{num}-{sub.lower()}"
    # pure numeric or numeric with sub without separator like "11b"
    m2 = re.match(r'^(\d+)\s*([a-z])\s*$', s)
    if m2:
        num, sub = m2.groups()
        return f"{num}-{sub.lower()}"
    # just number
    m3 = re.match(r'^(\d+)\s*$', s)
    if m3:
        return m3.group(1)
    # fallback clean: remove spaces/punct except dash
    s = re.sub(r'[^0-9a-z\-]', '', s)
    return s if s else None

def split_label(label: str) -> Tuple[str, Optional[str]]:
    """ '11-a' -> ('11','a'), '5' -> ('5', None) """
    if "-" in label:
        parts = label.split("-", 1)
        return parts[0], parts[1]
    return label, None

def question_id_from_label(label: str, sub: Optional[str]) -> str:
    if sub:
        return f"q_{label}_{sub}"
    return f"q_{label}"

def display_number(label: str, sub: Optional[str]) -> str:
    if sub:
        return f"{label} {sub}."
    return f"{label}"

def extract_label_from_text(text: str) -> Optional[str]:
    """
    Try to find label at start of answer text like "Q2." or "11 b)"
    Returns normalized or None
    """
    if not text:
        return None
    # check first line
    first = text.strip().split("\n")[0][:30]
    # patterns
    patterns = [
        r'^\s*(?:q\.?|question|ans\.?|answer)?\s*(\d+)\s*[\(\.\-]?\s*([a-zA-Z])\b',
        r'^\s*(?:q\.?|question|ans\.?|answer)?\s*(\d+)\b',
    ]
    for pat in patterns:
        m = re.match(pat, first, re.IGNORECASE)
        if m:
            groups = m.groups()
            if len(groups) == 2 and groups[1]:
                return normalize_label(f"{groups[0]}-{groups[1]}")
            elif groups[0]:
                # check if next char is sub letter separated: need to look ahead
                return normalize_label(groups[0])
    return None
