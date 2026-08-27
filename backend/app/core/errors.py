from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger

class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, details=None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)

async def app_error_handler(request: Request, exc: AppError):
    logger.error(f"AppError {exc.status_code}: {exc.message} {exc.details or ''}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "details": exc.details, "status_code": exc.status_code},
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "Validation error", "details": exc.errors()},
    )

async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "details": str(exc)},
    )
