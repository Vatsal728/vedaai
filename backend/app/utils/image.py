from PIL import Image, ImageEnhance
import os

def enhance_handwriting(image_path: str) -> str:
    """Optional pre-processing to improve OCR for handwriting: increase contrast"""
    try:
        im = Image.open(image_path)
        # mild contrast
        enhancer = ImageEnhance.Contrast(im)
        im = enhancer.enhance(1.15)
        im.save(image_path, "JPEG", quality=90)
    except Exception:
        pass
    return image_path
