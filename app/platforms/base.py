"""Contract every platform adapter must follow, plus shared helpers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx


class PlatformError(Exception):
    """An *expected* failure (bad token, rate limit, unexpected reply...).

    The message is shown to the API client in the ``error`` field, so it must
    never contain secrets.
    """


@dataclass(frozen=True)
class PostOutcome:
    """What an adapter returns after a successful post."""

    url: str
    public_access: bool


class BasePlatform(ABC):
    """Base class: one subclass per third-party platform."""

    name: str = "base"

    def missing_credentials(self) -> list[str]:
        """Names of required env variables that are not set."""
        return []

    @abstractmethod
    async def post(
        self, client: httpx.AsyncClient, message: str, link: str
    ) -> PostOutcome:
        """Publish *message* and return the public URL, or raise PlatformError."""

    # ---- helpers shared by the adapters ---------------------------------
    @staticmethod
    def _missing(**values: str | None) -> list[str]:
        """``_missing(MY_ENV_VAR=value)`` -> ['MY_ENV_VAR'] when value is empty."""
        return [env_name for env_name, value in values.items() if not value]

    @staticmethod
    def parse_json(response: httpx.Response, action: str) -> dict:
        """Return the JSON body as a dict or raise a readable PlatformError."""
        try:
            data = response.json()
        except ValueError:
            data = None

        if not response.is_success:
            detail = data if data is not None else response.text
            raise PlatformError(
                f"{action}: HTTP {response.status_code} - {str(detail)[:300]}"
            )
        if not isinstance(data, dict):
            raise PlatformError(f"{action}: unexpected response from platform")
        return data


def build_title(message: str, link: str, max_length: int = 60) -> str:
    """Short title for platforms that require one (Telegraph, DEV)."""
    text = " ".join(message.replace(link, "").split()).strip(" -:")
    if not text:
        return "New post"
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"