import json
import os
import re
from typing import List, Dict, Any, Tuple
from loguru import logger
from app.services.groq_service import groq_json_with_retry, mock_enabled
from app.core.config import settings
from app.utils.label import normalize_label, split_label

def load_prompt(name: str, replacements: Dict[str,str]) -> str:
    p = os.path.join(os.path.dirname(__file__), "..", "prompts", name)
    with open(p, "r", encoding="utf-8") as f:
        txt = f.read()
    for k,v in replacements.items():
        txt = txt.replace("{{"+k+"}}", v)
    return txt

def fallback_map(questions: List[Dict[str,Any]], answer_groups: List[Dict[str,Any]]) -> Tuple[List[Dict[str,Any]], List[Dict[str,Any]]]:
    """
    Deterministic mapping:
    - exact normalized label match
    - if multiple answers same label, keep first
    - unlabeled -> semantic fallback via keyword overlap (simple)
    Returns (mappings, orphans)
    """
    # Build question lookup by normalized label
    q_lookup = {}
    for q in questions:
        label = q["label"]
        sub = q.get("subLabel")
        norm = f"{label}-{sub}" if sub else label
        norm = normalize_label(norm)
        # store id mapping
        qid = q["id"] if "id" in q else f"q_{label}_{sub}" if sub else f"q_{label}"
        q_lookup[norm] = qid
        # also store without dash variant for fuzzy
        q_lookup[norm.replace("-", "")] = qid

    used_q = set()
    used_a = set()
    mappings: Dict[str, Dict[str,Any]] = {}
    # init all questions as unanswered
    for q in questions:
        qid = q["id"] if "id" in q else f"q_{q['label']}_{q.get('subLabel','')}" if q.get("subLabel") else f"q_{q['label']}"
        # canonical id
        label = q["label"]
        sub = q.get("subLabel")
        qid = f"q_{label}_{sub}" if sub else f"q_{label}"
        mappings[qid] = {"questionId": qid, "answerIds": [], "confidence": 0.0, "status": "unanswered"}

    orphans = []
    # First pass: exact label
    for idx, ag in enumerate(answer_groups):
        aid = f"a_{idx}"
        raw_label = ag.get("detectedLabel")
        norm = normalize_label(raw_label) if raw_label else None
        qid = None
        if norm:
            qid = q_lookup.get(norm) or q_lookup.get(norm.replace("-", ""))
        if qid and qid in mappings and not mappings[qid]["answerIds"]:
            mappings[qid]["answerIds"] = [aid]
            mappings[qid]["confidence"] = 0.95
            mappings[qid]["status"] = "answered"
            used_a.add(aid)
            used_q.add(qid)
        elif qid and qid in mappings and mappings[qid]["answerIds"]:
            # duplicate label -> mark orphan duplicate?
            orphans.append({"answerId": aid, "reason": f"duplicate for {qid}"})
            used_a.add(aid)
        else:
            # no label or no match -> try semantic fallback if unlabeled but text overlap
            if not norm:
                # simple semantic: find question with highest word overlap
                best_q = None
                best_score = 0
                ans_text = (ag.get("textPreview") or "").lower()
                ans_words = set(re.findall(r'\w+', ans_text))
                for q in questions:
                    qid2 = f"q_{q['label']}_{q['subLabel']}" if q.get("subLabel") else f"q_{q['label']}"
                    if mappings[qid2]["answerIds"]:
                        continue
                    q_words = set(re.findall(r'\w+', q.get("text","").lower()))
                    overlap = len(ans_words & q_words)
                    score = overlap / max(1, len(q_words))
                    if score > best_score and score > 0.12:
                        best_score = score
                        best_q = qid2
                if best_q:
                    mappings[best_q]["answerIds"] = [aid]
                    mappings[best_q]["confidence"] = round(min(0.85, best_score + 0.3), 2)
                    mappings[best_q]["status"] = "answered"
                    used_a.add(aid)
                else:
                    orphans.append({"answerId": aid, "reason": "no matching question"})
                    used_a.add(aid)
            else:
                orphans.append({"answerId": aid, "reason": f"label {raw_label} not found"})
                used_a.add(aid)

    # Convert mappings dict to list, preserve order of questions input
    out_mappings = []
    for q in questions:
        qid = f"q_{q['label']}_{q['subLabel']}" if q.get("subLabel") else f"q_{q['label']}"
        out_mappings.append(mappings[qid])

    # Merge orphans duplicates handling: already collected
    # If still unused answers (should not happen), mark orphan
    for idx, ag in enumerate(answer_groups):
        aid = f"a_{idx}"
        if aid not in used_a:
            orphans.append({"answerId": aid, "reason": "unmapped"})

    return out_mappings, orphans

def map_answers(questions: List[Dict[str,Any]], answer_groups: List[Dict[str,Any]]) -> Tuple[List[Dict[str,Any]], List[Dict[str,Any]]]:
    # Normalize question ids for prompt
    q_for_prompt = []
    for q in questions:
        label = q["label"]
        sub = q.get("subLabel")
        qid = f"q_{label}_{sub}" if sub else f"q_{label}"
        q_for_prompt.append({
            "id": qid,
            "label": label,
            "subLabel": sub,
            "text": q.get("text","")[:200]
        })
    a_for_prompt = []
    for idx, ag in enumerate(answer_groups):
        a_for_prompt.append({
            "id": f"a_{idx}",
            "detectedLabel": ag.get("detectedLabel"),
            "textPreview": ag.get("textPreview","")[:200]
        })

    if mock_enabled():
        logger.warning("Groq not configured, using deterministic mapping")
        return fallback_map(questions, answer_groups)

    q_json = json.dumps(q_for_prompt, ensure_ascii=False, indent=2)
    a_json = json.dumps(a_for_prompt, ensure_ascii=False, indent=2)
    prompt = load_prompt("mapping.txt", {"QUESTIONS_JSON": q_json, "ANSWERS_JSON": a_json})
    system = "You are a precise answer-to-question matcher. Return only valid JSON. No explanations."

    try:
        data = groq_json_with_retry(prompt, system=system, model=settings.groq_model_q, retries=1)
        # Expect {"mappings": [...], "orphans": [...]}
        if isinstance(data, list):
            # assume it's mappings directly
            mappings = data
            orphans = []
        elif isinstance(data, dict):
            mappings = data.get("mappings", [])
            orphans = data.get("orphans", [])
        else:
            raise ValueError("Invalid mapping response")

        # Validate and normalize
        # Build mapping dict
        mapping_by_q = {}
        for m in mappings:
            qid = m.get("questionId")
            if not qid:
                continue
            aids = m.get("answerIds", [])
            if isinstance(aids, str):
                aids = [aids]
            conf = float(m.get("confidence", 0.5))
            # status inferred
            status = "answered" if aids else "unanswered"
            mapping_by_q[qid] = {"questionId": qid, "answerIds": aids, "confidence": conf, "status": status}

        # Ensure all questions present
        out = []
        for q in q_for_prompt:
            qid = q["id"]
            if qid in mapping_by_q:
                out.append(mapping_by_q[qid])
            else:
                out.append({"questionId": qid, "answerIds": [], "confidence": 0, "status": "unanswered"})

        # Orphans normalize
        clean_orphans = []
        for o in orphans:
            if isinstance(o, dict) and "answerId" in o:
                clean_orphans.append(o)
            elif isinstance(o, str):
                clean_orphans.append({"answerId": o, "reason": "no match"})

        # Verify no duplicate answerIds across mappings
        seen = set()
        for m in out:
            for aid in m["answerIds"]:
                if aid in seen:
                    logger.warning(f"Duplicate answerId {aid} in mappings")
                seen.add(aid)
        # Any answer not in seen and not in orphans -> add to orphans
        all_aids = {a["id"] for a in a_for_prompt}
        mapped_aids = seen | {o["answerId"] for o in clean_orphans}
        for aid in all_aids - mapped_aids:
            clean_orphans.append({"answerId": aid, "reason": "unmapped by LLM"})

        logger.info(f"Groq mapping: {len([m for m in out if m['status']=='answered'])} answered, {len(clean_orphans)} orphans")
        return out, clean_orphans

    except Exception as e:
        logger.exception(f"Groq mapping failed, fallback: {e}")
        return fallback_map(questions, answer_groups)
