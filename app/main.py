"""FastAPI entry point:  uvicorn app.main:app --host 0.0.0.0 --port 4000"""

import logging
from functools import lru_cache

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.platforms import build_platforms
from app.schemas import PostingRequest, PostingResponse
from app.services.posting_service import PostingService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# httpx logs full request URLs at INFO level, and Telegram's URL contains the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(
    title="Automated Multi-Platform Posting API",
    description="Publishes one short message with a CTA link to several platforms.",
    version="1.0.0",
)


@lru_cache
def get_posting_service() -> PostingService:
    settings = get_settings()
    return PostingService(
        build_platforms(settings), timeout_seconds=settings.platform_timeout_seconds
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Turn pydantic's verbose errors into a compact, readable 422 body."""
    details = [
        {
            "field": ".".join(str(part) for part in err["loc"][1:]) or "body",
            "message": err["msg"].removeprefix("Value error, "),
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": "Validation failed", "details": details},
    )


@app.post("/posting", response_model=PostingResponse, tags=["posting"])
async def create_posting(
    payload: PostingRequest,
    service: PostingService = Depends(get_posting_service),
) -> PostingResponse:
    """Validate the message, then post it to every platform."""
    return await service.publish(payload.message, payload.cta_link)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}