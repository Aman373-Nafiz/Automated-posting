"""Pure validation helpers for the incoming message (no FastAPI code here)."""

import re

from pydantic import AnyHttpUrl, TypeAdapter, ValidationError

MAX_MESSAGE_LENGTH = 200

# Anything that *looks like* a link: http(s)://... or www....
_LINK_CANDIDATE = re.compile(r"(?:https?://|www\.)\S*", re.IGNORECASE)
# Punctuation that often follows a link in a sentence: "visit https://x.com."
_TRAILING_PUNCTUATION = ".,;:!?)]}'\""
_url_adapter = TypeAdapter(AnyHttpUrl)


def extract_single_link(message: str) -> str:
    """Return the one CTA link in *message* or raise ValueError."""
    candidates = [
        match.rstrip(_TRAILING_PUNCTUATION)
        for match in _LINK_CANDIDATE.findall(message)
    ]

    if not candidates:
        raise ValueError("Message must contain exactly one CTA link (found none)")
    if len(candidates) > 1:
        raise ValueError(
            f"Message must contain exactly one CTA link (found {len(candidates)})"
        )

    link = candidates[0]
    if not link.lower().startswith(("http://", "https://")):
        raise ValueError("The CTA link must start with http:// or https://")

    try:
        parsed = _url_adapter.validate_python(link)
    except ValidationError:
        raise ValueError(f"'{link}' is not a valid URL") from None

    # "http://localhost" or "http://abc" pass the parser but are not public links.
    if "." not in (parsed.host or ""):
        raise ValueError(f"'{link}' is not a valid public URL")

    return link


def validate_message(message: str) -> str:
    """Run every rule on the message and return it unchanged if valid."""
    if not message:
        raise ValueError("Message must not be empty")
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValueError(
            f"Message must not exceed {MAX_MESSAGE_LENGTH} characters "
            f"(received {len(message)})"
        )
    extract_single_link(message)
    return message