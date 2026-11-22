"""Orchestrates posting to every platform concurrently and in isolation."""

import asyncio
import logging
from collections.abc import Sequence
from datetime import datetime, timezone

import httpx

from app.platforms.base import BasePlatform, PlatformError
from app.schemas import PlatformResult, PostingResponse

logger = logging.getLogger(__name__)


class PostingService:
    def __init__(self, platforms: Sequence[BasePlatform], timeout_seconds: float = 20.0):
        self.platforms = list(platforms)
        self.timeout_seconds = timeout_seconds

    async def publish(self, message: str, link: str) -> PostingResponse:
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout_seconds)) as client:
            # All platforms run at the same time; one slow/broken platform
            # can neither block nor crash the others.
            results = await asyncio.gather(
                *(self._publish_one(client, p, message, link) for p in self.platforms)
            )
        return PostingResponse(
            success=any(r.status == "success" for r in results),
            results=list(results),
        )

    async def _publish_one(
        self, client: httpx.AsyncClient, platform: BasePlatform, message: str, link: str
    ) -> PlatformResult:
        missing = platform.missing_credentials()
        if missing:
            return self._failure(platform, f"Missing credentials: {', '.join(missing)}")

        try:
            outcome = await asyncio.wait_for(
                platform.post(client, message, link), timeout=self.timeout_seconds
            )
        except PlatformError as exc:
            return self._failure(platform, str(exc))
        except (asyncio.TimeoutError, httpx.TimeoutException):
            return self._failure(platform, f"Timed out after {self.timeout_seconds:g}s")
        except httpx.HTTPError as exc:
            # Only the exception *type* is exposed: its text may contain a URL
            # (e.g. the Telegram token is part of its URL).
            return self._failure(platform, f"Network error ({type(exc).__name__})")
        except Exception:  # noqa: BLE001 - a bug in one adapter must not break others
            logger.exception("Unexpected error while posting to %s", platform.name)
            return self._failure(platform, "Unexpected internal error")

        now = datetime.now(timezone.utc)
        return PlatformResult(
            platform=platform.name,
            status="success",
            posted_url=outcome.url,
            public_access=outcome.public_access,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            error=None,
        )

    @staticmethod
    def _failure(platform: BasePlatform, error: str) -> PlatformResult:
        return PlatformResult(
            platform=platform.name,
            status="failed",
            posted_url=None,
            public_access=False,
            date=None,
            time=None,
            error=error,
        )