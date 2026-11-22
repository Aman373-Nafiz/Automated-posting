"""Adapter tests using httpx.MockTransport: no internet and no real credentials."""

import asyncio
import json

import httpx

from app.config import Settings
from app.platforms.base import PlatformError, build_title
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.devto import DevToPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.telegram import TelegramPlatform
from app.platforms.telegraph import TelegraphPlatform
from app.platforms.writeas import WriteAsPlatform

LINK = "https://example.com"
MESSAGE = f"Grow your visibility today {LINK}"


def run(platform, handler):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await platform.post(client, MESSAGE, LINK)

    return asyncio.run(go())


def settings(**kw):
    return Settings(_env_file=None, **kw)


def test_telegraph_creates_account_then_page():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("createAccount"):
            return httpx.Response(200, json={"ok": True, "result": {"access_token": "t"}})
        return httpx.Response(200, json={"ok": True, "result": {"url": "https://telegra.ph/x"}})

    out = run(TelegraphPlatform(settings()), handler)
    assert out.url == "https://telegra.ph/x" and out.public_access
    assert calls == ["/createAccount", "/createPage"]


def test_telegraph_ok_false_is_an_error():
    handler = lambda r: httpx.Response(200, json={"ok": False, "error": "TITLE_REQUIRED"})
    try:
        run(TelegraphPlatform(settings(telegraph_access_token="t")), handler)
    except PlatformError as exc:
        assert "TITLE_REQUIRED" in str(exc)
    else:
        raise AssertionError("expected PlatformError")


def test_writeas_anonymous_post():
    handler = lambda r: httpx.Response(201, json={"code": 201, "data": {"id": "abc123"}})
    assert run(WriteAsPlatform(settings()), handler).url == "https://write.as/abc123"


def test_mastodon_sends_bearer_and_public_visibility():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer tok"
        assert json.loads(request.content)["visibility"] == "public"
        return httpx.Response(200, json={"url": "https://mastodon.social/@a/1", "visibility": "public"})

    out = run(MastodonPlatform(settings(mastodon_access_token="tok")), handler)
    assert out.url.endswith("/@a/1") and out.public_access


def test_bluesky_two_step_flow_and_link_facet():
    def handler(request):
        if request.url.path.endswith("createSession"):
            return httpx.Response(200, json={"accessJwt": "jwt", "did": "did:plc:1", "handle": "me.bsky.social"})
        body = json.loads(request.content)
        facet = body["record"]["facets"][0]["index"]
        text = body["record"]["text"].encode()
        assert text[facet["byteStart"]:facet["byteEnd"]] == LINK.encode()
        return httpx.Response(200, json={"uri": "at://did:plc:1/app.bsky.feed.post/3kabc"})

    p = BlueskyPlatform(settings(bluesky_handle="me.bsky.social", bluesky_app_password="pw"))
    assert run(p, handler).url == "https://bsky.app/profile/me.bsky.social/post/3kabc"


def test_devto_auth_error_is_readable():
    handler = lambda r: httpx.Response(401, json={"error": "unauthorized"})
    try:
        run(DevToPlatform(settings(devto_api_key="bad")), handler)
    except PlatformError as exc:
        assert "401" in str(exc)
    else:
        raise AssertionError("expected PlatformError")


def test_telegram_public_channel_url():
    handler = lambda r: httpx.Response(
        200, json={"ok": True, "result": {"message_id": 7, "chat": {"username": "mychan", "id": -100123}}}
    )
    p = TelegramPlatform(settings(telegram_bot_token="b", telegram_channel="@mychan"))
    out = run(p, handler)
    assert out.url == "https://t.me/mychan/7" and out.public_access


def test_missing_credentials_are_named():
    assert MastodonPlatform(settings()).missing_credentials() == ["MASTODON_ACCESS_TOKEN"]
    assert TelegramPlatform(settings()).missing_credentials() == ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHANNEL"]


def test_build_title_truncates():
    assert build_title("word " * 40 + LINK, LINK).endswith("…")
    assert build_title(LINK, LINK) == "New post"