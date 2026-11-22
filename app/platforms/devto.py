"""DEV Community (Forem API) - https://developers.forem.com/api/v1"""

import httpx

from app.config import Settings
from app.platforms.base import BasePlatform, PlatformError, PostOutcome, build_title


class DevToPlatform(BasePlatform):
    name = "DEV Community"
    api_url = "https://dev.to/api/articles"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def missing_credentials(self) -> list[str]:
        return self._missing(DEVTO_API_KEY=self.settings.devto_api_key)

    async def post(self, client: httpx.AsyncClient, message: str, link: str) -> PostOutcome:
        response = await client.post(
            self.api_url,
            headers={
                "api-key": self.settings.devto_api_key or "",
                "Accept": "application/vnd.forem.api-v1+json",
            },
            json={
                "article": {
                    "title": build_title(message, link),
                    "body_markdown": message,
                    "published": True,
                }
            },
        )
        data = self.parse_json(response, "create article")

        url = data.get("url")
        if not url:
            raise PlatformError("create article: response did not contain a URL")
        return PostOutcome(url=url, public_access=True)