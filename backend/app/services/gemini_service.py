import os
import base64
from typing import Optional, List
from loguru import logger
from app.core.config import settings

try:
    import google.generativeai as genai
    gemini_available = True
except ImportError:
    genai = None
    gemini_available = False

def get_gemini_configured() -> bool:
    key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
    return bool(key and key not in ["", "gsk_...", "AIza_fake"]) and gemini_available

def configure_gemini():
    if not gemini_available:
        logger.warning("google-generativeai not installed")
        return False
    key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
    if not key or key == "":
        logger.warning("GEMINI_API_KEY not configured — selective vision will be skipped")
        return False
    try:
        genai.configure(api_key=key)
        return True
    except Exception as e:
        logger.warning(f"Gemini configure failed: {e}")
        return False

def transcribe_handwriting_image(
    image_path: str,
    prompt: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[str]:
    """
    Selective vision for low-confidence handwriting / diagrams.
    Sends cropped page / full page image to Gemini and returns transcription.
    Fallback to None on failure (so pipeline continues with OCR text).
    """
    if not settings.enable_vision_fallback:
        return None
    if not get_gemini_configured():
        # Also try Groq vision as pure fallback if Gemini missing but Groq configured? keep silent
        return None
    if not configure_gemini():
        return None

    model = model or settings.gemini_vision_model or "gemini-2.0-flash"
    # Normalize deprecated model names
    model = settings.resolve_model(model) if hasattr(settings, "resolve_model") else model
    # Gemini model ids: ensure without prefix? google expects 'gemini-2.0-flash'
    # Strip 'openai/' etc if mistakenly passed
    if "/" in model:
        model = model.split("/")[-1]

    prompt = prompt or (
        "You are a handwriting transcription expert. Transcribe the student handwritten answer in this image exactly. "
        "Preserve question labels like Q1, 11(a). If there is a diagram, describe its labels (e.g., alveolar sac, capillary, gas exchange arrow). "
        "Return only the transcription text, no explanation. If illegible, say [illegible]."
    )

    try:
        from PIL import Image
        img = Image.open(image_path)
        # Downscale if huge to save tokens
        max_side = 1600
        if max(img.size) > max_side:
            ratio = max_side / max(img.size)
            img = img.resize((int(img.size[0]*ratio), int(img.size[1]*ratio)))

        gem_model = genai.GenerativeModel(model)
        logger.info(f"Gemini vision call model={model} image={os.path.basename(image_path)} size={img.size}")
        resp = gem_model.generate_content([prompt, img], generation_config={"temperature": 0, "max_output_tokens": 2048})
        text = ""
        if resp and resp.candidates:
            # Extract text parts
            for cand in resp.candidates:
                if cand.content and cand.content.parts:
                    for part in cand.content.parts:
                        if hasattr(part, "text") and part.text:
                            text += part.text + "\n"
        text = text.strip()
        if not text and hasattr(resp, "text"):
            text = resp.text.strip()
        logger.info(f"Gemini vision success len={len(text)} preview={text[:120]}")
        return text if text else None
    except Exception as e:
        logger.warning(f"Gemini vision failed for {image_path}: {e}")
        return None

def transcribe_images_selective(
    image_paths: List[str],
    ocr_confidences: List[float],
    threshold: float = 0.55,
) -> List[Optional[str]]:
    """
    For each page, if avg OCR confidence < threshold or diagram suspected, call Gemini.
    Returns list aligned with image_paths with transcription or None.
    """
    results: List[Optional[str]] = []
    for idx, path in enumerate(image_paths):
        conf = ocr_confidences[idx] if idx < len(ocr_confidences) else 1.0
        # Only call if low confidence or suspected diagram (checked via filename? we do conf only here)
        if conf < threshold:
            txt = transcribe_handwriting_image(path)
            results.append(txt)
        else:
            results.append(None)
    return results

def fallback_groq_vision_transcribe(image_path: str) -> Optional[str]:
    """Optional Groq llava fallback if Gemini not available but Groq vision wanted — currently not used (OCR exactness preferred)."""
    # Kept for reference: Groq llava-v1.6-34b can be called via Groq API with base64 image if needed.
    # Not implemented to keep dependencies minimal; OCR + Gemini selective is more reliable.
    return None
