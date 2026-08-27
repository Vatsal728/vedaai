import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from loguru import logger

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.errors import AppError, app_error_handler, validation_exception_handler, generic_exception_handler
from app.store.memory_store import init_store
from app.api.v1.router import api_router

setup_logging()

app = FastAPI(
    title="VedaAI Assessment Mapping API",
    version="1.0.0",
    description="Hybrid Groq+OCR backend for question extraction, answer mapping, grading",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.cors_origins_list != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Routers
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    init_store(ttl_minutes=settings.session_ttl_minutes, tmp_dir=settings.tmp_dir_abs)
    os.makedirs(settings.tmp_dir_abs, exist_ok=True)
    logger.info(f"Startup: tmp_dir={settings.tmp_dir_abs} groq_configured={bool(settings.groq_api_key and settings.groq_api_key != 'gsk_...')} cors={settings.cors_origins_list}")

@app.get("/")
async def root():
    return {
        "ok": True,
        "service": "VedaAI Hybrid Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }

@app.get("/health")
async def health_root():
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)
