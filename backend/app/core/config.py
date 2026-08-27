from pydantic_settings import BaseSettings
from typing import List, ClassVar, Dict
import os

class Settings(BaseSettings):
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    groq_api_key: str = ""
    # Reliable Groq free tier models (Aug 2026 catalog) — only 2 text
    groq_model_q: str = "openai/gpt-oss-120b"  # high-capacity reasoning (Q extract, grading)
    groq_model_fast: str = "openai/gpt-oss-20b"  # fast lightweight (answer grouping, mapping)
    # Gemini selective vision for low-confidence handwriting / diagrams (Option B)
    gemini_api_key: str = ""
    gemini_vision_model: str = "gemini-2.0-flash"  # alt: gemini-2.5-flash ; more reliable than llava for handwriting
    groq_vision_model: str = "llava-v1.6-34b"  # kept as pure-Groq fallback if Gemini not configured
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000"
    max_file_size_mb: int = 10
    session_ttl_minutes: int = 45
    tmp_dir: str = "./tmp/sessions"
    ocr_use_gpu: bool = False
    enable_vision_fallback: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"

    # Catalog helpers — only reliable (ClassVar so not treated as fields)
    GROQ_CATALOG: ClassVar[Dict[str, str]] = {
        "openai/gpt-oss-120b": "High-capacity reasoning",
        "openai/gpt-oss-20b": "Fast lightweight",
        "llava-v1.6-34b": "Groq vision multimodal (fallback)",
        "gemini-2.0-flash": "Gemini vision selective for handwriting/diagrams",
        "gemini-2.5-flash": "Gemini vision high-accuracy alt",
    }
    DEPRECATED_MAP: ClassVar[Dict[str, str]] = {
        "llama-3.1-8b-instant": "openai/gpt-oss-20b",
        "llama3-8b-8192": "openai/gpt-oss-20b",
        "llama-3.3-70b-versatile": "openai/gpt-oss-120b",
        "llama3-70b-8192": "openai/gpt-oss-120b",
        "llama-3.2-11b-vision-preview": "llava-v1.6-34b",
        "llama-3.2-90b-vision-preview": "llava-v1.6-34b",
    }

    def resolve_model(self, model: str) -> str:
        """Map deprecated ids to new catalog, warn if needed."""
        if model in self.DEPRECATED_MAP:
            # lazy import to avoid circular
            try:
                from loguru import logger
                logger.warning(f"Deprecated Groq model '{model}' -> migrated to '{self.DEPRECATED_MAP[model]}' (Aug 2026 retirement)")
            except:
                pass
            return self.DEPRECATED_MAP[model]
        return model

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def tmp_dir_abs(self) -> str:
        # Resolve relative to backend folder
        if os.path.isabs(self.tmp_dir):
            return self.tmp_dir
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base, self.tmp_dir)

settings = Settings()
