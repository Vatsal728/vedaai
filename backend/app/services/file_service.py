import os
import shutil
import uuid
from typing import Tuple, List
from fastapi import UploadFile
from loguru import logger
from app.core.errors import AppError
from app.utils.pdf_to_image import normalize_images, get_image_dimensions
from app.core.config import settings

ALLOWED_MIME = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
ALLOWED_EXT = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}

def validate_file(file: UploadFile):
    if not file.filename:
        raise AppError("File must have a name", 400)
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        raise AppError(f"Unsupported file type {ext}. Allowed: {ALLOWED_EXT}", 400)
    # mime check is lenient (browser may send octet-stream)
    if file.content_type and file.content_type not in ALLOWED_MIME and file.content_type != "application/octet-stream":
        logger.warning(f"Unexpected mime {file.content_type} for {file.filename}, allowing based on ext")

async def save_and_process(file: UploadFile, session_dir: str, prefix: str) -> Tuple[str, List[str], dict]:
    """
    Save uploaded file to session_dir/original/, convert to images in session_dir/{prefix}_images/
    Returns (saved_path, image_paths, file_info)
    """
    validate_file(file)
    orig_dir = os.path.join(session_dir, "original")
    os.makedirs(orig_dir, exist_ok=True)
    ext = os.path.splitext(file.filename)[1].lower()
    if not ext:
        ext = ".pdf" if file.content_type == "application/pdf" else ".jpg"
    saved_name = f"{prefix}{ext}"
    saved_path = os.path.join(orig_dir, saved_name)

    # Save
    file.file.seek(0)
    content = await file.read()
    size = len(content)
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if size > max_bytes:
        raise AppError(f"File {file.filename} too large ({size/1024/1024:.1f}MB). Max {settings.max_file_size_mb}MB", 413)
    if size == 0:
        raise AppError(f"File {file.filename} is empty", 400)
    with open(saved_path, "wb") as f:
        f.write(content)
    logger.info(f"Saved {file.filename} -> {saved_path} {size} bytes")

    # Convert to images
    images_dir = os.path.join(session_dir, f"{prefix}_images")
    try:
        image_paths = normalize_images(saved_path, images_dir, dpi=200)
    except Exception as e:
        logger.exception(f"Failed to render images for {saved_path}: {e}")
        raise AppError(f"Failed to process file {file.filename}: {e}", 422)

    file_info = {
        "name": file.filename,
        "saved_path": saved_path,
        "pages": len(image_paths),
        "mime": file.content_type or "unknown",
        "size": size,
        "images": image_paths,
    }
    return saved_path, image_paths, file_info

def get_session_dir(session_id: str) -> str:
    base = settings.tmp_dir_abs
    return os.path.join(base, session_id)

def ensure_session_dir(session_id: str) -> str:
    d = get_session_dir(session_id)
    os.makedirs(d, exist_ok=True)
    return d

def cleanup_session(session_id: str):
    d = get_session_dir(session_id)
    if os.path.exists(d):
        try:
            shutil.rmtree(d)
            logger.info(f"Cleaned session dir {d}")
        except Exception as e:
            logger.warning(f"Failed to clean {d}: {e}")
