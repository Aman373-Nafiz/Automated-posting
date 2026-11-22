"""Application settings, loaded from environment variables / a local .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every credential lives here, so no secret is ever hard-coded."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # General
    platform_timeout_seconds: float = 20.0

    # Telegraph (token optional - an account is created automatically)
    telegraph_access_token: str | None = None

    # Write.as (token optional - anonymous posting is supported)
    writeas_access_token: str | None = None

    # Mastodon
    mastodon_base_url: str = "https://mastodon.social"
    mastodon_access_token: str | None = None

    # Bluesky
    bluesky_service_url: str = "https://bsky.social"
    bluesky_handle: str | None = None
    bluesky_app_password: str | None = None

    # DEV Community (dev.to)
    devto_api_key: str | None = None

    # Telegram
    telegram_bot_token: str | None = None
    telegram_channel: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Create the settings once and reuse them."""
    return Settings()