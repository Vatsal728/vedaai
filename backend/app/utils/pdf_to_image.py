import fitz  # PyMuPDF
from PIL import Image
import io
import os
from typing import List, Tuple
from loguru import logger

def pdf_to_images(pdf_path: str, out_dir: str, dpi: int = 200, prefix: str = "page") -> List[str]:
    """
    Convert PDF to images. Returns list of image paths.
    """
    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    images = []
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_path = os.path.join(out_dir, f"{prefix}_{i}.jpg")
        pix.save(img_path, "jpeg", jpg_quality=85)
        images.append(img_path)
        logger.info(f"Rendered {pdf_path} page {i} -> {img_path} {pix.w}x{pix.h}")
    doc.close()
    return images

def image_to_image(src_path: str, out_dir: str, prefix: str = "page") -> List[str]:
    """For single image uploads, normalize and save as jpg, return list with one entry"""
    os.makedirs(out_dir, exist_ok=True)
    try:
        im = Image.open(src_path)
        if im.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        elif im.mode != "RGB":
            im = im.convert("RGB")
        # resize if too large, keep aspect
        max_side = 2048
        if max(im.size) > max_side:
            ratio = max_side / max(im.size)
            new_size = (int(im.size[0]*ratio), int(im.size[1]*ratio))
            im = im.resize(new_size, Image.LANCZOS)
        out_path = os.path.join(out_dir, f"{prefix}_0.jpg")
        im.save(out_path, "JPEG", quality=90)
        logger.info(f"Normalized image {src_path} -> {out_path} {im.size}")
        return [out_path]
    except Exception as e:
        logger.error(f"image_to_image failed {e}")
        raise

def is_pdf(path: str) -> bool:
    return path.lower().endswith(".pdf")

def get_image_dimensions(image_path: str) -> Tuple[int, int]:
    with Image.open(image_path) as im:
        return im.size

def normalize_images(file_path: str, out_dir: str, dpi: int = 200) -> List[str]:
    if is_pdf(file_path):
        return pdf_to_images(file_path, out_dir, dpi=dpi)
    else:
        return image_to_image(file_path, out_dir)
