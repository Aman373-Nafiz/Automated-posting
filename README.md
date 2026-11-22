# Automated Multi-Platform Posting API

A **FastAPI** service with one endpoint, `POST /posting`. It validates a short
message that contains one CTA link and publishes it to **6 platforms
concurrently**. Each platform is handled independently, so if one fails the
others still post.

| # | Platform | API used | Credentials needed |
|---|----------|----------|--------------------|
| 1 | Telegraph | `api.telegra.ph` (createAccount / createPage) | none (account auto-created) |
| 2 | Write.as | `POST write.as/api/posts` | none (anonymous post) |
| 3 | Mastodon | `POST /api/v1/statuses` | access token |
| 4 | Bluesky | AT Protocol `createSession` + `createRecord` | handle + app password |
| 5 | DEV Community | Forem API `POST /api/articles` | API key |
| 6 | Telegram | Bot API `sendMessage` to a public channel | bot token + channel |

> X/Twitter, LinkedIn, Reddit and Medium were evaluated and skipped: they need
> a paid API tier, app review, or no longer issue API tokens.

## Architecture

```
app/
├── main.py                  # FastAPI app, route, dependency injection, error handler
├── config.py                # Settings from env vars / .env (pydantic-settings)
├── schemas.py               # Request / response models
├── validators.py            # Message rules (length, exactly one valid link)
├── platforms/
│   ├── base.py              # BasePlatform contract, PlatformError, PostOutcome
│   ├── __init__.py          # Registry: build_platforms()
│   └── telegraph.py, writeas.py, mastodon.py, bluesky.py, devto.py, telegram.py
└── services/
    └── posting_service.py   # Concurrent, failure-isolated orchestration
tests/                       # test_posting.py (API + service), test_adapters.py (mocked HTTP)
```

Request flow: **route → validation → PostingService → (all platforms in parallel) → response**.

## Setup

Requires Python 3.10+.

```bash
git clone <your-repo-url> && cd automated-posting
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in your own credentials
```

### Getting credentials (all free)
- **Mastodon** – *Preferences → Development → New application*, scope `write:statuses`, copy "Your access token".
- **Bluesky** – *Settings → Privacy and security → App passwords*.
- **DEV** – *Settings → Extensions → Generate API key*.
- **Telegram** – talk to `@BotFather` (`/newbot`), create a **public** channel, add the bot as admin (post permission), set `TELEGRAM_CHANNEL=@yourchannel`.
- **Telegraph / Write.as** – nothing required.

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Swagger UI: <http://localhost:4000/docs>

## API

### `POST /posting`

```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out our latest business platform and grow your online visibility. https://example.com"}'
```

Response `200` (`success` is `true` when at least one platform succeeded):

```json
{
  "success": true,
  "results": [
    {
      "platform": "Telegraph",
      "status": "success",
      "posted_url": "https://telegra.ph/Check-out-our-latest-business-platform-11-21",
      "public_access": true,
      "date": "2026-11-21",
      "time": "10:30:00",
      "error": null
    },
    {
      "platform": "DEV Community",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Missing credentials: DEVTO_API_KEY"
    }
  ]
}
```

Date and time are **UTC**. A platform without credentials is reported as
`"Missing credentials: <ENV_VAR>"`.

### Validation errors – `422`

```json
{
  "success": false,
  "error": "Validation failed",
  "details": [
    { "field": "message", "message": "Message must contain exactly one CTA link (found 2)" }
  ]
}
```

Rules: message ≤ 200 characters (after trimming) · exactly one link · link must
be a valid `http(s)` URL with a real domain.

## Tests

```bash
pytest -v
```

The tests use fake platforms and `httpx.MockTransport`, so they need no
internet and no credentials.

## Adding a platform
1. Create `app/platforms/<name>.py` with a class extending `BasePlatform` (`name`, `post()`, optionally `missing_credentials()`).
2. Add its settings to `config.py` and `.env.example`.
3. Add one line to `build_platforms()` in `app/platforms/__init__.py`.

## Design decisions
- **Concurrency**: `asyncio.gather` + a per-platform timeout, so total latency ≈ the slowest platform.
- **Isolation**: every platform call is wrapped; expected errors, timeouts, network errors and unexpected bugs all become a `failed` result.
- **Security**: secrets only come from env vars; `.env` is git-ignored; httpx request logging is silenced because Telegram's URL contains the bot token; network error details never expose URLs.
- **HTTP status**: `200` for any valid request (inspect `success` / `results`), `422` for invalid input.

## Screenshots / logs
Add your own screenshots of `/docs` and a real run to `docs/screenshots/`.