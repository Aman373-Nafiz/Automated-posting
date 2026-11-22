"""Mastodon - https://docs.joinmastodon.org/methods/statuses/#create"""

import uuid

import httpx

from app.config import Settings
from app.platforms.base import BasePlatform, PlatformError, PostOutcome


class MastodonPlatform(BasePlatform):
    name = "Mastodon"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def missing_credentials(self) -> list[str]:
        return self._missing(MASTODON_ACCESS_TOKEN=self.settings.mastodon_access_token)

    async def post(self, client: httpx.AsyncClient, message: str, link: str) -> PostOutcome:
        base_url = self.settings.mastodon_base_url.rstrip("/")
        response = await client.post(
            f"{base_url}/api/v1/statuses",
            headers={
                "Authorization": f"Bearer {self.settings.mastodon_access_token}",
                # Prevents a duplicate toot if the request is ever retried.
                "Idempotency-Key": str(uuid.uuid4()),
            },
            json={"status": message, "visibility": "public"},
        )
        data = self.parse_json(response, "create status")

        url = data.get("url")
        if not url:
            raise PlatformError("create status: response did not contain a URL")
        return PostOutcome(url=url, public_access=data.get("visibility") == "public")