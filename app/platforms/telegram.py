"""Telegram Bot API - https://core.telegram.org/bots/api#sendmessage"""

import httpx

from app.config import Settings
from app.platforms.base import BasePlatform, PlatformError, PostOutcome


class TelegramPlatform(BasePlatform):
    name = "Telegram"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def missing_credentials(self) -> list[str]:
        return self._missing(
            TELEGRAM_BOT_TOKEN=self.settings.telegram_bot_token,
            TELEGRAM_CHANNEL=self.settings.telegram_channel,
        )

    async def post(self, client: httpx.AsyncClient, message: str, link: str) -> PostOutcome:
        response = await client.post(
            f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage",
            json={"chat_id": self.settings.telegram_channel, "text": message},
        )
        # Telegram reports errors as {"ok": false, "description": "..."}
        data = self.parse_json(response, "sendMessage")
        if not data.get("ok"):
            raise PlatformError(f"sendMessage: {data.get('description', 'unknown error')}")

        result = data["result"]
        message_id = result["message_id"]
        chat = result.get("chat", {})

        if chat.get("username"):  # public channel -> https://t.me/<name>/<id>
            return PostOutcome(
                url=f"https://t.me/{chat['username']}/{message_id}", public_access=True
            )
        # Private channel: link only works for members.
        internal_id = str(chat.get("id", "")).removeprefix("-100")
        return PostOutcome(
            url=f"https://t.me/c/{internal_id}/{message_id}", public_access=False
        )