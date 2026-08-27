import json
import os
from typing import Optional, Dict, Any
from loguru import logger
from app.core.config import settings

try:
    from groq import Groq
    groq_available = True
except ImportError:
    Groq = None
    groq_available = False

def get_groq_client():
    if not groq_available:
        logger.warning("groq library not installed")
        return None
    api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY", "")
    if not api_key or api_key == "gsk_...":
        logger.warning("GROQ_API_KEY not configured")
        return None
    return Groq(api_key=api_key)

def groq_chat(
    prompt: str,
    model: Optional[str] = None,
    system: str = "You are a helpful assistant that returns valid JSON only.",
    temperature: float = 0,
    max_tokens: int = 4096,
    json_mode: bool = True,
) -> str:
    client = get_groq_client()
    if client is None:
        raise RuntimeError("Groq client not configured. Set GROQ_API_KEY in .env")

    model = model or settings.groq_model_q
    # auto-migrate deprecated ids
    try:
        model = settings.resolve_model(model)
    except:
        pass
    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    logger.info(f"Groq call model={model} prompt_len={len(prompt)} json={json_mode}")
    try:
        resp = client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content
        logger.info(f"Groq response len={len(content)} usage={resp.usage}")
        return content
    except Exception as e:
        logger.exception(f"Groq call failed: {e}")
        raise

def parse_groq_json(text: str) -> Any:
    """Robust JSON parse with fallback to extract ```json block"""
    text = text.strip()
    # strip markdown fences
    if "```" in text:
        import re
        m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # try to find outermost json array/object
        import re
        # find first [ or { and last matching
        start_arr = text.find("[")
        start_obj = text.find("{")
        if start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
            end = text.rfind("]")
            if end != -1:
                cand = text[start_arr:end+1]
                return json.loads(cand)
        elif start_obj != -1:
            end = text.rfind("}")
            if end != -1:
                cand = text[start_obj:end+1]
                return json.loads(cand)
        logger.error(f"JSON parse failed: {e} text={text[:500]}")
        raise

def groq_json_with_retry(prompt: str, system: str, model: Optional[str] = None, retries: int = 1) -> Any:
    last_err = None
    for attempt in range(retries + 1):
        try:
            raw = groq_chat(prompt, model=model, system=system, json_mode=True)
            return parse_groq_json(raw)
        except Exception as e:
            last_err = e
            logger.warning(f"Groq json attempt {attempt} failed: {e}")
            if attempt < retries:
                # repair prompt
                prompt = prompt + "\n\nIMPORTANT: Return ONLY valid JSON, no explanation, no markdown."
                continue
            raise last_err

# Mock fallback for testing without API key
def mock_enabled() -> bool:
    return not settings.groq_api_key or settings.groq_api_key == "" or settings.groq_api_key == "gsk_..."
