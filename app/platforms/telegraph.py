"""Telegraph (telegra.ph) - https://telegra.ph/api"""

import json

import httpx

from app.config import Settings
from app.platforms.base import BasePlatform, PlatformError, PostOutcome, build_title


class TelegraphPlatform(BasePlatform):
    name = "Telegraph"
    api_url = "https://api.telegra.ph"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        # Reused across requests; created on first use when not configured.
        self._token: str | None = settings.telegraph_access_token or None

    async def _ensure_token(self, client: httpx.AsyncClient) -> str:
        if self._token:
            return self._token
        response = await client.post(
            f"{self.api_url}/createAccount",
            data={"short_name": "autoposter", "author_name": "Auto Poster"},
        )
        self._token = self._result(response, "createAccount")["access_token"]
        return self._token

    def _result(self, response: httpx.Response, action: str) -> dict:
        # Telegraph answers HTTP 200 even on errors: {"ok": false, "error": "..."}
        data = self.parse_json(response, action)
        if not data.get("ok"):
            raise PlatformError(f"{action}: {data.get('error', 'unknown error')}")
        return data["result"]

    async def post(self, client: httpx.AsyncClient, message: str, link: str) -> PostOutcome:
        token = await self._ensure_token(client)

        before, _, after = message.partition(link)
        children = [
            part
            for part in (
                before,
                {"tag": "a", "attrs": {"href": link}, "children": [link]},
                after,
            )
            if part != ""
        ]
        content = [{"tag": "p", "children": children}]

        response = await client.post(
            f"{self.api_url}/createPage",
            data={
                "access_token": token,
                "title": build_title(message, link),
                "content": json.dumps(content),
            },
        )
        page = self._result(response, "createPage")
        return PostOutcome(url=page["url"], public_access=True)