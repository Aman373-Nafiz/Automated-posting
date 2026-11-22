"""Write.as - https://developers.write.as/docs/api/"""

import httpx

from app.config import Settings
from app.platforms.base import BasePlatform, PlatformError, PostOutcome


class WriteAsPlatform(BasePlatform):
    name = "Write.as"
    api_url = "https://write.as/api/posts"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def post(self, client: httpx.AsyncClient, message: str, link: str) -> PostOutcome:
        headers = {}
        if self.settings.writeas_access_token:
            headers["Authorization"] = f"Token {self.settings.writeas_access_token}"

        response = await client.post(
            self.api_url, json={"body": message, "font": "norm"}, headers=headers
        )
        data = self.parse_json(response, "create post")

        post_id = (data.get("data") or {}).get("id")
        if not post_id:
            raise PlatformError("create post: response did not contain a post id")
        return PostOutcome(url=f"https://write.as/{post_id}", public_access=True)