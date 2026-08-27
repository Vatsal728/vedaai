import os
from typing import List, Dict, Any, Tuple
from loguru import logger
from app.core.config import settings

# Lazy import so backend can start even if rapidocr not installed
_ocr_engine = None

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is not None:
        return _ocr_engine
    try:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine = RapidOCR()
        logger.info("RapidOCR initialized")
        return _ocr_engine
    except Exception as e:
        logger.warning(f"RapidOCR not available: {e}, will try pytesseract fallback")
        _ocr_engine = "fallback"
        return _ocr_engine

def ocr_image(image_path: str, page_index: int) -> Tuple[List[Dict[str, Any]], str]:
    """
    OCR single image. Returns (blocks, full_text)
    blocks: [{id, text, bbox:[[x1,y1]...], score, pageIndex, img_w, img_h}]
    """
    from PIL import Image
    with Image.open(image_path) as im:
        img_w, img_h = im.size

    engine = get_ocr_engine()
    blocks: List[Dict[str, Any]] = []
    full_text_parts: List[str] = []

    if engine == "fallback" or engine is None:
        # Use pytesseract if available, else simple mock
        try:
            import pytesseract
            from PIL import Image as PILImage
            im = PILImage.open(image_path)
            data = pytesseract.image_to_data(im, output_type=pytesseract.Output.DICT)
            # group by line? For now create one block per word
            idx = 0
            for i in range(len(data["text"])):
                txt = data["text"][i].strip()
                if not txt:
                    continue
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                box = [[x, y], [x+w, y], [x+w, y+h], [x, y+h]]
                blocks.append({
                    "id": idx,
                    "text": txt,
                    "bbox": box,
                    "score": float(data["conf"][i]) / 100 if data["conf"][i] != -1 else 0.9,
                    "pageIndex": page_index,
                    "img_w": img_w,
                    "img_h": img_h,
                })
                idx += 1
                full_text_parts.append(txt)
            logger.info(f"Fallback OCR page {page_index}: {len(blocks)} word blocks")
        except Exception as e:
            logger.warning(f"Fallback OCR failed {e}, returning mock block")
            # Mock: return whole page as one block to allow pipeline to proceed without OCR
            # This enables testing without OCR deps
            blocks = [{
                "id": 0,
                "text": f"[MOCK OCR page {page_index} - install rapidocr-onnxruntime for real OCR]",
                "bbox": [[10, 10], [img_w-10, 10], [img_w-10, img_h-10], [10, img_h-10]],
                "score": 0.5,
                "pageIndex": page_index,
                "img_w": img_w,
                "img_h": img_h,
            }]
            full_text_parts = [b["text"] for b in blocks]
    else:
        try:
            result, elapse = engine(image_path)
            # result is list of [box, txt, score] or None
            if result is None:
                result = []
            for idx, (box, txt, score) in enumerate(result):
                # box is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                txt = txt.strip()
                if not txt:
                    continue
                blocks.append({
                    "id": idx,
                    "text": txt,
                    "bbox": box,
                    "score": float(score),
                    "pageIndex": page_index,
                    "img_w": img_w,
                    "img_h": img_h,
                })
                full_text_parts.append(txt)
            logger.info(f"RapidOCR page {page_index}: {len(blocks)} blocks elapse={elapse}")
        except Exception as e:
            logger.exception(f"RapidOCR failed on {image_path}: {e}")
            # return mock
            blocks = [{
                "id": 0,
                "text": f"[OCR error page {page_index}: {e}]",
                "bbox": [[10, 10], [img_w-10, 10], [img_w-10, img_h-10], [10, img_h-10]],
                "score": 0.3,
                "pageIndex": page_index,
                "img_w": img_w,
                "img_h": img_h,
            }]
            full_text_parts = [b["text"] for b in blocks]

    full_text = " ".join(full_text_parts)
    return blocks, full_text

def ocr_images(image_paths: List[str]) -> Tuple[List[Dict[str, Any]], List[str], str, List[float]]:
    """
    OCR all images. Returns (all_blocks with global id, per_page_texts, concatenated_text, per_page_avg_conf)
    per_page_avg_conf used for selective Gemini vision trigger (low confidence).
    """
    all_blocks: List[Dict[str, Any]] = []
    per_page_texts: List[str] = []
    per_page_confs: List[float] = []
    global_id = 0
    for page_idx, path in enumerate(image_paths):
        blocks, full_text = ocr_image(path, page_idx)
        # avg confidence for this page
        avg_conf = sum(b.get("score", 0.9) for b in blocks) / max(1, len(blocks))
        per_page_confs.append(avg_conf)
        # reassign global ids and keep pageIndex
        for b in blocks:
            b["id"] = global_id
            b["orig_id"] = b["id"]
            global_id += 1
            all_blocks.append(b)
        per_page_texts.append(full_text)
        logger.info(f"Page {page_idx} OCR text len={len(full_text)} avg_conf={avg_conf:.2f} preview={full_text[:120]}")

    # concatenated with page markers for LLM
    concatenated = ""
    for i, txt in enumerate(per_page_texts):
        concatenated += f"\n[PAGE {i+1}]\n{txt}\n"
    return all_blocks, per_page_texts, concatenated, per_page_confs

def group_blocks_into_answers(blocks: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Heuristic grouping: sort blocks by page and y, then split where large vertical gap.
    Used as fallback if Groq grouping not available.
    """
    if not blocks:
        return []
    # sort by page, then y top
    def top_y(b):
        return min(p[1] for p in b["bbox"])
    sorted_blocks = sorted(blocks, key=lambda b: (b["pageIndex"], top_y(b)))
    # naive: group every N blocks or gap > threshold
    groups: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    last_y = None
    last_page = None
    median_h = 30  # approximate
    # estimate median height
    heights = [max(p[1] for p in b["bbox"]) - min(p[1] for p in b["bbox"]) for b in sorted_blocks]
    if heights:
        heights.sort()
        median_h = heights[len(heights)//2]

    for b in sorted_blocks:
        y = top_y(b)
        if last_page is not None and (b["pageIndex"] != last_page or (last_y is not None and y - last_y > median_h * 1.8)):
            # big gap -> new group if current not empty and next block looks like new question label
            # check if b text looks like label
            txt = b["text"].strip()
            import re
            is_label = re.match(r'^\s*(Q\.?|Question|\d+)\s*[\.\)]?\s*[a-zA-Z]?', txt, re.IGNORECASE)
            if is_label and current:
                groups.append(current)
                current = []
        current.append(b)
        last_y = max(p[1] for p in b["bbox"])
        last_page = b["pageIndex"]
    if current:
        groups.append(current)
    return groups
