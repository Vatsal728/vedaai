import re
import json
import os
from typing import List, Dict, Any
from loguru import logger
from app.services.groq_service import groq_json_with_retry, mock_enabled
from app.core.config import settings
from app.utils.label import normalize_label
from app.services.ocr_service import group_blocks_into_answers

def load_prompt(name: str, replacements: Dict[str,str]) -> str:
    p = os.path.join(os.path.dirname(__file__), "..", "prompts", name)
    with open(p, "r", encoding="utf-8") as f:
        txt = f.read()
    for k,v in replacements.items():
        txt = txt.replace("{{"+k+"}}", v)
    return txt

def fallback_group_blocks(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Heuristic: detect label at start of line groups
    """
    # Use grouping helper then assign labels
    groups = group_blocks_into_answers(blocks)
    answer_groups = []
    for gi, grp in enumerate(groups):
        # concatenate texts
        text = " ".join(b["text"] for b in grp)
        # detect label in first block
        first_txt = grp[0]["text"] if grp else ""
        label = None
        m = re.match(r'^\s*(?:q\.?|ans\.?)?\s*(\d+)\s*[\(\.]?\s*([a-zA-Z])?\b', first_txt, re.IGNORECASE)
        if m:
            num = m.group(1)
            sub = m.group(2)
            if sub and sub.lower() in "abcdefgh":
                label = normalize_label(f"{num}-{sub}")
            else:
                label = normalize_label(num)
        else:
            # also check first 20 chars of joined text
            m2 = re.search(r'\bQ\s*(\d+)\b', text[:30], re.IGNORECASE)
            if m2:
                label = normalize_label(m2.group(1))
        answer_groups.append({
            "detectedLabel": label,
            "blockIds": [b["id"] for b in grp],
            "textPreview": text[:400]
        })
    if not answer_groups and blocks:
        # single group fallback
        text = " ".join(b["text"] for b in blocks)
        answer_groups.append({
            "detectedLabel": None,
            "blockIds": [b["id"] for b in blocks],
            "textPreview": text[:400]
        })
    # If mock OCR (contains MOCK), generate plausible mock answers for testing
    has_mock = any("MOCK" in b["text"] for b in blocks)
    if has_mock:
        logger.warning("Mock OCR detected, returning mock answer groups for testing")
        return mock_answer_groups()
    return answer_groups

def mock_answer_groups() -> List[Dict[str, Any]]:
    # Simulate student answered Q1, Q2, Q3 correctly, Q4 wrong/missing, etc. For 14 groups ?
    # Needs blockIds placeholder; pipeline will later handle bbox via mock blocks.
    # Provide 10 answers: Q1, Q2, Q3, Q5, Q6, Q8, Q9, Q11a, Q12, Q13, and one orphan
    return [
        {"detectedLabel": "1", "blockIds": [0], "textPreview": "Photosynthesis is the process used by green plants... 6CO2 + 6H2O -> C6H12O6 + 6O2"},
        {"detectedLabel": "2", "blockIds": [1], "textPreview": "The process mainly occurs in the chloroplast of the plant cell. It has two main stages: 1. Light reaction..."},
        {"detectedLabel": "3", "blockIds": [2], "textPreview": "Chloroplasts contain chlorophyll pigment... Light reaction captures energy, Dark reaction makes glucose."},
        {"detectedLabel": "5", "blockIds": [3], "textPreview": "Diagram of alveolus with alveolar sac, capillary, gas exchange arrow"},
        {"detectedLabel": "6", "blockIds": [4], "textPreview": "Diagram of digestive system labelled stomach small intestine etc. Absorption in small intestine."},
        {"detectedLabel": "8", "blockIds": [5], "textPreview": "Palisade mesophyll tightly packed, spongy loosely with air spaces..."},
        {"detectedLabel": "9", "blockIds": [6], "textPreview": "Transpiration is loss of water via stomata, increased by temperature and wind."},
        {"detectedLabel": "11-a", "blockIds": [7], "textPreview": "Plant A broad green, Plant B pale elongated due low light."},
        {"detectedLabel": "12", "blockIds": [8], "textPreview": "Tidal volume 0.5L *12 =6L per minute"},
        {"detectedLabel": None, "blockIds": [9], "textPreview": "Extra doodle or rough work not related to any question"},
    ]

def extract_answers(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not blocks:
        return []

    # If no API key, fallback directly
    if mock_enabled():
        logger.warning("Groq not configured, using heuristic answer grouping")
        return fallback_group_blocks(blocks)

    # Prepare blocks JSON for LLM (truncate if too large)
    blocks_for_llm = []
    for b in blocks[:200]:  # limit
        blocks_for_llm.append({
            "id": b["id"],
            "text": b["text"][:120],
            "pageIndex": b["pageIndex"]
        })
    blocks_json = json.dumps(blocks_for_llm, ensure_ascii=False, indent=2)[:14000]

    prompt = load_prompt("answer_group.txt", {"BLOCKS_JSON": blocks_json})
    system = "You are a document layout parser. Return only valid JSON array. No explanations."
    try:
        data = groq_json_with_retry(prompt, system=system, model=settings.groq_model_fast, retries=1)
                # normalize
        if isinstance(data, dict):
            if "answers" in data:
                data = data["answers"]
            elif "blockIds" in data:
                data = [data]
            else:
                for k, v in data.items():
                    if isinstance(v, list):
                        data = v
                        break
        if not isinstance(data, list):
            raise ValueError(f"Expected list got {type(data)}")
        # validate
        cleaned = []
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            label = item.get("detectedLabel")
            if label:
                label = normalize_label(str(label))
            block_ids = item.get("blockIds", [])
            # ensure ints
            block_ids = [int(x) for x in block_ids if isinstance(x, (int,str)) and str(x).isdigit()]
            if not block_ids:
                continue
            text = str(item.get("textPreview", ""))[:400]
            if not text:
                # reconstruct from blocks
                txt_parts = [b["text"] for b in blocks if b["id"] in block_ids]
                text = " ".join(txt_parts)[:400]
            cleaned.append({
                "detectedLabel": label,
                "blockIds": block_ids,
                "textPreview": text
            })
        logger.info(f"Groq grouped {len(cleaned)} answers")
        if not cleaned:
            raise ValueError("Empty Groq grouping")
        return cleaned
    except Exception as e:
        logger.exception(f"Groq answer grouping failed, fallback: {e}")
        return fallback_group_blocks(blocks)
