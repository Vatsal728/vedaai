import asyncio
import traceback
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger
from app.store.memory_store import get_store
from app.services.ocr_service import ocr_images
from app.services.question_extractor import extract_questions
from app.services.answer_extractor import extract_answers
from app.services.mapper import map_answers
from app.services.grading import grade_answers
from app.utils.bbox import merge_block_bboxes
from app.utils.label import normalize_label
from app.models.enums import SessionStatus

def update_progress(session_id: str, status: str, progress: int, extra: dict = None):
    store = get_store()
    sess = store.get(session_id)
    if not sess:
        return
    patch = {"status": status, "progress": progress, "updatedAt": datetime.utcnow()}
    if extra:
        patch.update(extra)
    store.update(session_id, patch)
    logger.info(f"Session {session_id} -> {status} {progress}%")

async def run_pipeline(session_id: str, question_images: List[str], answer_images: List[str]):
    """
    Main pipeline: OCR -> Q extract -> A extract -> BBox merge -> Mapping -> Grading
    Runs in background asyncio task.
    """
    try:
        update_progress(session_id, SessionStatus.extracting_questions, 15)
        # OCR both sets in parallel (threadpool)
        loop = asyncio.get_event_loop()
        # Question OCR (printed -> high confidence, no vision needed)
        logger.info(f"Pipeline {session_id}: OCR question {len(question_images)} pages")
        q_blocks, q_per_page, q_concat, q_confs = await loop.run_in_executor(None, lambda: ocr_images(question_images))
        # Answer OCR
        logger.info(f"Pipeline {session_id}: OCR answer {len(answer_images)} pages")
        a_blocks, a_per_page, a_concat, a_confs = await loop.run_in_executor(None, lambda: ocr_images(answer_images))
        # Selective Gemini vision for low-confidence handwriting / diagrams
        try:
            from app.core.config import settings
            from app.services.gemini_service import transcribe_images_selective
            if settings.enable_vision_fallback:
                # 1. Question Paper Handwritten Fallback (avg conf < 0.80)
                need_q_vision = [c < 0.80 for c in q_confs]
                if any(need_q_vision) or any('MACK' in b['text'] for b in q_blocks):
                    logger.info(f"Pipeline {session_id}: Selective Gemini vision for Question Paper")
                    q_gemini = await loop.run_in_executor(
                        None, lambda: transcribe_images_selective(question_images, q_confs, threshold=0.80)
                    )
                    q_per_page = [gtxt if gtxt else orig for orig, gtxt in zip(q_per_page, q_gemini)]
                    q_concat = ""
                    for i, txt in enumerate(q_per_page):
                        q_concat += f"\n[PAGE {i+1}]\n{txt}\n"

                # 2. Answer Sheet Handwritten Fallback (avg conf < 0.85)
                need_vision = [c < 0.85 for c in a_confs]
                if any(need_vision):
                    pages_needed = [i for i, need in enumerate(need_vision) if need]
                    logger.info(f"Pipeline {session_id}: Selective Gemini vision for pages {pages_needed}")
                    gemini_texts = await loop.run_in_executor(
                        None, lambda: transcribe_images_selective(answer_images, a_confs, threshold=0.85)
                    )
                    a_per_page = [gtxt if gtxt else orig for orig, gtxt in zip(a_per_page, gemini_texts)]
                    a_concat = ""
                    for i, txt in enumerate(a_per_page):
                        a_concat += f"\n[PAGE {i+1}]\n{txt}\n"
                    
                    # Re-build a_blocks with Gemini transcriptions to feed high-quality text to answer extractor
                    new_a_blocks = []
                    # keep blocks from pages that don't need vision
                    for b in a_blocks:
                        pid = b["pageIndex"]
                        if not need_vision[pid] or gemini_texts[pid] is None:
                            new_a_blocks.append(b)
                    
                    # add new blocks for transcribed pages
                    next_block_id = max([b["id"] for b in a_blocks], default=0) + 1
                    for pid, gtxt in enumerate(gemini_texts):
                        if need_vision[pid] and gtxt is not None:
                            # Split transcription lines robustly by finding question labels in the middle
                            import re
                            label_pattern = re.compile(r'(?<=.)(?=\b(?:Ans|Q|Question)?\s*\d+\s*[\(\.]?\s*[a-zA-Z]?[\)\.]?\b)', re.IGNORECASE)
                            glines = []
                            for rl in gtxt.split('\n'):
                                for part in label_pattern.split(rl):
                                    if part.strip():
                                        glines.append(part.strip())
                            for line in glines:
                                new_a_blocks.append({
                                    "id": next_block_id,
                                    "text": line,
                                    "pageIndex": pid,
                                    "bbox": [[0, 0], [1000, 0], [1000, 1000], [0, 1000]],
                                    "img_w": 1000,
                                    "img_h": 1000,
                                    "confidence": 0.99
                                })
                                next_block_id += 1
                    a_blocks = new_a_blocks
        except Exception as e:
            logger.warning(f"Selective vision step skipped: {e}")
    # Store OCR debug
        store = get_store()
        sess = store.get(session_id)
        if not sess:
            logger.error(f"Session {session_id} not found mid-pipeline")
            return

        # Stage: Question Extraction (Groq or heuristic)
        update_progress(session_id, SessionStatus.extracting_questions, 35)
        logger.info(f"Pipeline {session_id}: Extracting questions from {len(q_concat)} chars")
        raw_questions = await loop.run_in_executor(None, lambda: extract_questions(q_concat, q_per_page))
        # Normalize to final Question schema
        questions = []
        for idx, rq in enumerate(raw_questions):
            label = rq["label"]
            sub = rq.get("subLabel")
            # canonical id
            qid = f"q_{label}_{sub}" if sub else f"q_{label}"
            # display
            display = f"{label} {sub}." if sub else f"{label}"
            max_score = rq.get("maxScore")
            # ensure not None for display: later grading will fill defaults
            # need dimension for pageHint? not yet
            questions.append({
                "id": qid,
                "label": label,
                "subLabel": sub,
                "displayNumber": display,
                "text": rq.get("text",""),
                "order": rq.get("order", idx),
                "maxScore": max_score,
                "pageHint": rq.get("pageHint"),
                "type": rq.get("type","short")
            })
        logger.info(f"Pipeline {session_id}: Got {len(questions)} questions")

        update_progress(session_id, SessionStatus.extracting_answers, 55, {"questions": questions})

        # Stage: Answer Extraction
        logger.info(f"Pipeline {session_id}: Extracting answers from {len(a_blocks)} blocks")
        answer_groups = await loop.run_in_executor(None, lambda: extract_answers(a_blocks))
        logger.info(f"Pipeline {session_id}: Got {len(answer_groups)} answer groups")

        # Build AnswerRegion with BBoxes
        answer_regions = []
        for idx, ag in enumerate(answer_groups):
            aid = f"a_{idx}"
            block_ids = ag.get("blockIds", [])
            # compute bboxes from a_blocks
            bboxes = merge_block_bboxes(a_blocks, block_ids, page_width=1000, page_height=1000)  # size already normalized via img_w in blocks but fallback uses 1000
            # Actually merge function already uses img_w/h from blocks
            pages = sorted(list({b["pageIndex"] for b in bboxes})) if bboxes else []
            # If bboxes empty but we have blocks, fallback to block bboxes directly
            if not bboxes and block_ids:
                # create naive per block bbox normalized 0.1 padding
                for bid in block_ids:
                    blk = next((b for b in a_blocks if b["id"] == bid), None)
                    if blk:
                        # convert absolute to norm
                        box = blk["bbox"]
                        xs = [p[0] for p in box]
                        ys = [p[1] for p in box]
                        img_w = blk.get("img_w", 1000)
                        img_h = blk.get("img_h", 1000)
                        bboxes.append({
                            "pageIndex": blk["pageIndex"],
                            "x": round(min(xs)/img_w, 4),
                            "y": round(min(ys)/img_h, 4),
                            "w": round((max(xs)-min(xs))/img_w, 4),
                            "h": round((max(ys)-min(ys))/img_h, 4),
                        })
                        if blk["pageIndex"] not in pages:
                            pages.append(blk["pageIndex"])
            answer_regions.append({
                "id": aid,
                "detectedLabel": ag.get("detectedLabel"),
                "textPreview": ag.get("textPreview","")[:500],
                "blockIds": block_ids,
                "bboxes": bboxes,
                "pages": pages,
                "confidence": ag.get("confidence", 0.9)
            })

        update_progress(session_id, SessionStatus.mapping, 75, {"answers": answer_regions})

        # Stage: Mapping
        logger.info(f"Pipeline {session_id}: Mapping {len(questions)} Q x {len(answer_regions)} A")
        mappings, orphans = await loop.run_in_executor(None, lambda: map_answers(questions, answer_groups))
        # Convert mappings to schema (add status)
        # Already has status, ensure all questions present
        # Orphans are answers not mapped, but mappings already represent unanswered; orphans separate for summary
        logger.info(f"Pipeline {session_id}: Mapping done {len([m for m in mappings if m['status']=='answered'])} answered")

        update_progress(session_id, SessionStatus.grading, 85, {"mappings": mappings, "orphans": orphans})

        # Stage: Grading
        logger.info(f"Pipeline {session_id}: Grading")
        gradings = await loop.run_in_executor(None, lambda: grade_answers(questions, answer_groups, mappings))
        logger.info(f"Pipeline {session_id}: Grading done {len(gradings)}")

        # Summary
        answered = len([m for m in mappings if m["status"]=="answered"])
        unanswered = len([m for m in mappings if m["status"]=="unanswered"])
        orphan_count = len(orphans)
        total = sum(g["score"] for g in gradings)
        max_total = sum(g["maxScore"] for g in gradings)
        # overall feedback
        pct = (total / max_total * 100) if max_total else 0
        if pct >= 80:
            overall = f"Excellent work! {answered}/{len(questions)} answered, {total:.0f}/{max_total:.0f} ({pct:.0f}%). Keep it up!"
        elif pct >= 60:
            overall = f"Good effort! {answered}/{len(questions)} answered, {total:.0f}/{max_total:.0f} ({pct:.0f}%). Focus on unanswered areas."
        elif pct >= 40:
            overall = f"Needs improvement. {unanswered} unanswered, {total:.0f}/{max_total:.0f} ({pct:.0f}%). Revise key concepts."
        else:
            overall = f"Requires significant revision. {unanswered} unanswered, {orphan_count} unmatched. {total:.0f}/{max_total:.0f} ({pct:.0f}%)."

        summary = {
            "totalScore": round(total,1),
            "maxTotal": round(max_total,1),
            "answered": answered,
            "unanswered": unanswered,
            "orphan": orphan_count,
            "overallFeedback": overall
        }

        # Ensure questions have maxScore filled from grading if missing
        # Update maxScore in questions from gradings
        g_lookup = {g["questionId"]: g for g in gradings}
        for q in questions:
            qid = q["id"]
            if qid in g_lookup:
                q["maxScore"] = g_lookup[qid]["maxScore"]

        update_progress(session_id, SessionStatus.done, 100, {
            "questions": questions,
            "answers": answer_regions,
            "mappings": mappings,
            "grading": gradings,
            "summary": summary,
            "orphans": orphans
        })
        logger.info(f"Pipeline {session_id}: DONE summary {summary}")

    except Exception as e:
        logger.exception(f"Pipeline {session_id} failed: {e} {traceback.format_exc()}")
        update_progress(session_id, SessionStatus.error, 100, {"error": str(e)[:500]})
