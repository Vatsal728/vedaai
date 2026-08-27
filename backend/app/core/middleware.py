import time
import uuid
from fastapi import Request
from loguru import logger

async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    logger.info(f"[{request_id}] {request.method} {request.url.path} -> {response.status_code} {duration:.1f}ms")
    response.headers["X-Request-ID"] = request_id
    return response
