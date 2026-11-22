import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app, get_posting_service
from app.platforms.base import BasePlatform, PlatformError, PostOutcome
from app.services.posting_service import PostingService
from app.validators import extract_single_link

VALID = "Check out our platform and grow your visibility. https://example.com"


# ---------- fake platforms (no network needed) ----------
class OkPlatform(BasePlatform):
    name = "Ok"

    async def post(self, client, message, link):
        return PostOutcome(url="https://ok.example/post/1", public_access=True)


class FailingPlatform(BasePlatform):
    name = "Failing"

    async def post(self, client, message, link):
        raise PlatformError("Authentication failed")


class CrashingPlatform(BasePlatform):
    name = "Crashing"

    async def post(self, client, message, link):
        raise RuntimeError("boom")


class SlowPlatform(BasePlatform):
    name = "Slow"

    async def post(self, client, message, link):
        await asyncio.sleep(5)


class UnconfiguredPlatform(BasePlatform):
    name = "Unconfigured"

    def missing_credentials(self):
        return ["FAKE_TOKEN"]

    async def post(self, client, message, link):
        raise AssertionError("must not be called without credentials")


@pytest.fixture
def client():
    service = PostingService(
        [OkPlatform(), FailingPlatform(), CrashingPlatform(), UnconfiguredPlatform()],
        timeout_seconds=1,
    )
    app.dependency_overrides[get_posting_service] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------- validation ----------
@pytest.mark.parametrize(
    "message, expected",
    [
        ("Visit https://example.com today", "https://example.com"),
        ("Visit https://example.com.", "https://example.com"),  # trailing dot
        ("(see https://example.com/a?b=1)", "https://example.com/a?b=1"),
    ],
)
def test_extract_valid_link(message, expected):
    assert extract_single_link(message) == expected


@pytest.mark.parametrize(
    "message",
    [
        "No link here",
        "Two https://a.com and https://b.com",
        "Same twice https://a.com https://a.com",
        "Missing scheme www.example.com",
        "Bad host https://localhost/x",
        "Broken https://",
    ],
)
def test_extract_invalid_link(message):
    with pytest.raises(ValueError):
        extract_single_link(message)


def test_message_too_long(client):
    r = client.post("/posting", json={"message": "a" * 190 + " https://example.com"})
    assert r.status_code == 422
    assert "200 characters" in r.json()["details"][0]["message"]


def test_message_exactly_200_chars_is_accepted(client):
    link = " https://example.com"
    r = client.post("/posting", json={"message": "a" * (200 - len(link)) + link})
    assert r.status_code == 200


def test_missing_message_field(client):
    assert client.post("/posting", json={}).status_code == 422


def test_no_link_is_rejected(client):
    assert client.post("/posting", json={"message": "hello"}).status_code == 422


def test_two_links_are_rejected(client):
    r = client.post("/posting", json={"message": "https://a.com https://b.com"})
    assert r.status_code == 422


# ---------- posting behaviour ----------
def test_one_failure_does_not_stop_others(client):
    body = client.post("/posting", json={"message": VALID}).json()
    by_name = {r["platform"]: r for r in body["results"]}

    assert body["success"] is True
    assert by_name["Ok"]["status"] == "success"
    assert by_name["Ok"]["posted_url"] == "https://ok.example/post/1"
    assert by_name["Ok"]["public_access"] is True
    assert by_name["Ok"]["date"] and by_name["Ok"]["time"]

    assert by_name["Failing"]["status"] == "failed"
    assert by_name["Failing"]["error"] == "Authentication failed"
    assert by_name["Failing"]["date"] is None

    assert by_name["Crashing"]["error"] == "Unexpected internal error"
    assert "FAKE_TOKEN" in by_name["Unconfigured"]["error"]


def test_success_false_when_everything_fails():
    service = PostingService([FailingPlatform()], timeout_seconds=1)
    result = asyncio.run(service.publish(VALID, "https://example.com"))
    assert result.success is False


def test_slow_platform_times_out():
    service = PostingService([SlowPlatform(), OkPlatform()], timeout_seconds=0.1)
    result = asyncio.run(service.publish(VALID, "https://example.com"))
    by_name = {r.platform: r for r in result.results}
    assert "Timed out" in by_name["Slow"].error
    assert by_name["Ok"].status == "success"