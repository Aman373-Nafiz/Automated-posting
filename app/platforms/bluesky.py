"""Bluesky (AT Protocol) - https://docs.bsky.app/docs/tutorials/creating-a-post"""

from datetime import datetime, timezone

import httpx

from app.config import Settings
from app.platforms.base import BasePlatform, PlatformError, PostOutcome


class BlueskyPlatform(BasePlatform):
    name = "Bluesky"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def missing_credentials(self) -> list[str]:
        return self._missing(
            BLUESKY_HANDLE=self.settings.bluesky_handle,
            BLUESKY_APP_PASSWORD=self.settings.bluesky_app_password,
        )

    @staticmethod
    def _link_facet(message: str, link: str) -> list[dict]:
        """Make the URL clickable. Bluesky wants UTF-8 *byte* offsets."""
        text_bytes = message.encode("utf-8")
        link_bytes = link.encode("utf-8")
        start = text_bytes.find(link_bytes)
        if start == -1:
            return []
        return [
            {
                "index": {"byteStart": start, "byteEnd": start + len(link_bytes)},
                "features": [{"$type": "app.bsky.richtext.facet#link", "uri": link}],
            }
        ]

    async def post(self, client: httpx.AsyncClient, message: str, link: str) -> PostOutcome:
        service = self.settings.bluesky_service_url.rstrip("/")

        # Step 1 - log in with the app password to get a short-lived JWT.
        session_resp = await client.post(
            f"{service}/xrpc/com.atproto.server.createSession",
            json={
                "identifier": self.settings.bluesky_handle,
                "password": self.settings.bluesky_app_password,
            },
        )
        session = self.parse_json(session_resp, "login")

        # Step 2 - create a record of type app.bsky.feed.post in our repo.
        record = {
            "$type": "app.bsky.feed.post",
            "text": message,
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "facets": self._link_facet(message, link),
        }
        create_resp = await client.post(
            f"{service}/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {session['accessJwt']}"},
            json={
                "repo": session["did"],
                "collection": "app.bsky.feed.post",
                "record": record,
            },
        )
        created = self.parse_json(create_resp, "create post")

        # uri looks like: at://did:plc:xxxx/app.bsky.feed.post/<rkey>
        uri = created.get("uri")
        if not uri:
            raise PlatformError("create post: response did not contain a uri")
        rkey = uri.rsplit("/", 1)[-1]
        handle = session.get("handle", self.settings.bluesky_handle)
        return PostOutcome(
            url=f"https://bsky.app/profile/{handle}/post/{rkey}", public_access=True
        )