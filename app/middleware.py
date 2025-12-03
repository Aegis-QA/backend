from fastapi import Request
import logging

logger = logging.getLogger(__name__)

async def log_request_middleware(request: Request, call_next):
    logger.info(f"REQUEST: {request.method} {request.url.path}")
    if request.method == "POST" and "upload" in request.url.path:
        # Log form data keys
        form = await request.form()
        logger.info(f"Form keys: {list(form.keys())}")
        logger.info(f"Form values (names only): {[(k, type(v).__name__) for k, v in form.items()]}")
    response = await call_next(request)
    return response
