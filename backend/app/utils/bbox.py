from typing import List, Dict, Any

def merge_block_bboxes(blocks: List[Dict[str, Any]], block_ids: List[int], page_width: int, page_height: int) -> List[Dict[str, float]]:
    """
    Given OCR blocks with bbox [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] absolute, merge to normalized BBox per page.
    If blocks span multiple pages, returns multiple BBoxes grouped by page.
    """
    selected = [b for b in blocks if b["id"] in block_ids]
    if not selected:
        return []
    # group by page
    from collections import defaultdict
    by_page = defaultdict(list)
    for b in selected:
        by_page[b["pageIndex"]].append(b)

    bboxes = []
    for page_idx, blks in by_page.items():
        xs = []
        ys = []
        img_w = blks[0].get("img_w", page_width)
        img_h = blks[0].get("img_h", page_height)
        for b in blks:
            box = b["bbox"]  # [[x1,y1],...]
            for x, y in box:
                xs.append(x)
                ys.append(y)
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        # normalize 0-1 with padding 2%
        pad_w = (x_max - x_min) * 0.02
        pad_h = (y_max - y_min) * 0.02
        x_min = max(0, x_min - pad_w)
        y_min = max(0, y_min - pad_h)
        x_max = min(img_w, x_max + pad_w)
        y_max = min(img_h, y_max + pad_h)
        bboxes.append({
            "pageIndex": page_idx,
            "x": round(x_min / img_w, 4),
            "y": round(y_min / img_h, 4),
            "w": round((x_max - x_min) / img_w, 4),
            "h": round((y_max - y_min) / img_h, 4),
        })
    # sort by pageIndex
    bboxes.sort(key=lambda b: b["pageIndex"])
    return bboxes

def clamp_bbox(b: dict) -> dict:
    b["x"] = max(0, min(1, b["x"]))
    b["y"] = max(0, min(1, b["y"]))
    b["w"] = max(0.01, min(1 - b["x"], b["w"]))
    b["h"] = max(0.01, min(1 - b["y"], b["h"]))
    return b

def expand_bbox(b: dict, pad: float = 0.015) -> dict:
    b["x"] = max(0, b["x"] - pad)
    b["y"] = max(0, b["y"] - pad)
    b["w"] = min(1 - b["x"], b["w"] + 2*pad)
    b["h"] = min(1 - b["y"], b["h"] + 2*pad)
    return b
