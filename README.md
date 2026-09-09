# QR Generator Service

Standalone, reusable QR code generation. Deliberately has **no
knowledge of any other service's data** — a "URL" QR code is just a
plain string you provide, not a foreign key into some other app's
database. That's what makes this reusable across projects: link
shortener, an inventory system, a business-card tool, anything that
needs a QR code just sends it a string.

## Two ways to use it

**Stateless (`POST /render`)** — send content, get an image back
immediately, nothing saved, never trackable. Auth: `X-API-Key`
(simplest, no tenant context) or a bearer token.

**Persisted, tenant-scoped (`POST /codes`, `GET /codes`, ...)** —
requires a real bearer token from an [identity-service](../identity-service)
(or any RS256-issuing auth service exposing a public key the same way).
Saved codes are scoped to the token's `tenant_id` — a token from tenant
A can never see or delete tenant B's codes, verified by test.

## Scan tracking (dynamic QR)
A persisted `type="url"` code doesn't encode the destination URL
directly — it encodes a tracking redirect (`GET /s/{scan_code}`) that
logs the scan (device, browser, country, referrer) before forwarding
to the real destination. This is what makes it a genuinely *dynamic*
QR code, the same pattern used by every commercial dynamic-QR platform:
the printed code never changes, but you can see who scanned it and
when, and you can even redirect it somewhere new later without
reprinting anything. `type="text"/"wifi"/"vcard"` have no redirect step
and are never trackable — consistent with how every competing platform
treats static vs. dynamic codes.

Per-code analytics: `GET /codes/{id}/scans` (individual scan records),
`GET /codes/{id}/stats` (aggregate). Portfolio-wide: `GET /stats`.

## Web console
A minimal dashboard at `/console` — paste an access token (from your
identity service), see your QR codes and live scan charts, generate
new ones. It's a real UI backed by the same JSON API documented below,
not a separate code path.

## Quick start (Docker)
```bash
cp .env.example .env
# edit .env: set API_KEY, and IDENTITY_PUBLIC_KEY_URL if using /codes
docker compose up --build
```
Runs at `http://localhost:8002`. Console at `http://localhost:8002/console`.

### Running alongside identity-service
If both services are on the same Docker network, point
`IDENTITY_PUBLIC_KEY_URL` at `http://identity-service:8000/public-key`
(adjust the host/port to match how you've named/exposed that container).
No shared secret between the two services — this one only ever holds a
*public* key, fetched over HTTP and cached in memory.

## Quick start (local, no Docker)
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```
Docs at `/docs`. Tests: `pytest -v`.

## Types
| Type | Required field(s) |
|---|---|
| `url` | `url` — any string; this service doesn't validate or care what it points to |
| `text` | `text` |
| `wifi` | `wifi_ssid` (optional: `wifi_password`, `wifi_security`: WPA/WEP/nopass, `wifi_hidden`) |
| `vcard` | `vcard_name` (optional: `vcard_phone`, `vcard_email`, `vcard_org`) |

`fg_color`/`bg_color` (hex, PNG only — SVG is always black-on-transparent).
`format`: `png` or `svg`, only used by `/render`.

## Example: link-shortener calling this service
Instead of generating QR codes in-process (as the current
`link-shortener` repo still does — this is a newer, decoupled version
of that same capability), a future version of it would call:
```bash
curl -X POST http://qr-generator:8000/render \
  -H "X-API-Key: YOUR_KEY" -H "Content-Type: application/json" \
  -d '{"type": "url", "url": "https://aria-haross.ir/r/abc123"}' \
  --output qrcode.png
```
link-shortener still owns the click-tracking and the actual short URL;
this service only ever turns "some URL" into an image. That boundary
is what keeps it reusable — it never needs a code change to work with
a second, third, or tenth calling project.

## Security notes
- `API_KEY` grants stateless rendering with no tenant attribution —
  fine for embedding/quick use, but anything generated this way isn't
  tied to a tenant and can't be listed or managed later. Use a real
  bearer token (`/codes`) when you need that.
- If `IDENTITY_PUBLIC_KEY_URL` is unreachable at startup, the public
  key is fetched lazily on first use and cached — a transient network
  blip doesn't require a restart, but a token can't be verified until
  the fetch succeeds at least once.
