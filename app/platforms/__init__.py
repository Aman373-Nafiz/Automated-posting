"""Platform registry: the ONLY place to touch when adding a new platform."""

from app.config import Settings
from app.platforms.base import BasePlatform
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.devto import DevToPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.telegram import TelegramPlatform
from app.platforms.telegraph import TelegraphPlatform
from app.platforms.writeas import WriteAsPlatform


def build_platforms(settings: Settings) -> list[BasePlatform]:
    return [
        TelegraphPlatform(settings),
        WriteAsPlatform(settings),
        MastodonPlatform(settings),
        BlueskyPlatform(settings),
        DevToPlatform(settings),
        TelegramPlatform(settings),
    ]