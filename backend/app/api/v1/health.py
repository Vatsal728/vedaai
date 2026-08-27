from fastapi import APIRouter
from app.core.config import settings
from app.models.schemas import HealthResponse

router = APIRouter()

@router.get("", response_model=HealthResponse)
async def health():
    groq_ok = bool(settings.groq_api_key and settings.groq_api_key != "" and settings.groq_api_key != "gsk_...")
    return HealthResponse(ok=True, version="1.0.0", groqConfigured=groq_ok)

@router.get("/ready")
async def ready():
    return {"ready": True}
