"""
Tests generate their own RSA keypair and sign test JWTs locally, so this
test suite doesn't depend on a running identity-service - it tests the
actual verification logic (RS256, issuer check, claims extraction)
against a real signature, same as the manual cross-service test already
proved against the real identity-service.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_PEM = _key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()
_PUBLIC_PEM = _key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()

import os  # noqa: E402
os.environ["IDENTITY_PUBLIC_KEY_PEM"] = _PUBLIC_PEM

from app.main import app  # noqa: E402
from app.database import Base, get_db, engine, SessionLocal  # noqa: E402

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

API_KEY = {"X-API-Key": "test-api-key-123"}


def make_token(tenant_id=1, user_id=1, role="owner", issuer="identity-service"):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id), "username": "testuser", "tenant_id": tenant_id, "role": role,
        "iss": issuer, "iat": now, "exp": now + timedelta(minutes=30),
    }
    return jwt.encode(payload, _PRIVATE_PEM, algorithm="RS256")


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client():
    return TestClient(app)


# ---- /render (stateless) ------------------------------------------------

def test_render_url_via_api_key(client):
    r = client.post("/render", json={"type": "url", "url": "https://example.com/x"}, headers=API_KEY)
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert len(r.content) > 100


def test_render_svg_format(client):
    r = client.post("/render", json={"type": "text", "text": "hello", "format": "svg"}, headers=API_KEY)
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/svg+xml"


def test_render_via_valid_jwt_instead_of_api_key(client):
    token = make_token()
    r = client.post("/render", json={"type": "text", "text": "hi"}, headers=auth(token))
    assert r.status_code == 200


def test_render_no_auth_rejected(client):
    r = client.post("/render", json={"type": "text", "text": "hi"})
    assert r.status_code == 401


def test_render_wrong_api_key_rejected(client):
    r = client.post("/render", json={"type": "text", "text": "hi"}, headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_render_wifi_and_vcard_types(client):
    r = client.post("/render", json={"type": "wifi", "wifi_ssid": "Net1", "wifi_password": "pw123456"}, headers=API_KEY)
    assert r.status_code == 200
    r2 = client.post("/render", json={"type": "vcard", "vcard_name": "Test Person"}, headers=API_KEY)
    assert r2.status_code == 200


def test_render_missing_required_field_400(client):
    r = client.post("/render", json={"type": "url"}, headers=API_KEY)
    assert r.status_code == 400


# ---- /codes (persisted, tenant-scoped) -----------------------------------

def test_codes_requires_jwt_api_key_alone_insufficient(client):
    r = client.post("/codes", json={"type": "url", "url": "https://example.com"}, headers=API_KEY)
    assert r.status_code == 401


def test_create_and_list_code(client):
    token = make_token(tenant_id=100)
    r = client.post("/codes", json={"type": "url", "url": "https://example.com/a"}, headers=auth(token))
    assert r.status_code == 200

    r2 = client.get("/codes", headers=auth(token))
    assert r2.status_code == 200
    assert len(r2.json()) >= 1


def test_tenant_isolation_on_codes(client):
    token_a = make_token(tenant_id=200)
    r = client.post("/codes", json={"type": "text", "text": "tenant A secret"}, headers=auth(token_a))
    qr_id = r.json()["id"]

    token_b = make_token(tenant_id=201)
    r2 = client.get(f"/codes/{qr_id}/image", headers=auth(token_b))
    assert r2.status_code == 404

    r3 = client.get("/codes", headers=auth(token_b))
    assert all(c["id"] != qr_id for c in r3.json())


def test_delete_code_scoped_to_tenant(client):
    token_a = make_token(tenant_id=300)
    r = client.post("/codes", json={"type": "text", "text": "to delete"}, headers=auth(token_a))
    qr_id = r.json()["id"]

    token_b = make_token(tenant_id=301)
    r2 = client.delete(f"/codes/{qr_id}", headers=auth(token_b))
    assert r2.status_code == 404

    r3 = client.delete(f"/codes/{qr_id}", headers=auth(token_a))
    assert r3.status_code == 200


def test_wrong_issuer_rejected(client):
    bad_token = make_token(issuer="some-other-service")
    r = client.post("/codes", json={"type": "url", "url": "https://example.com"}, headers=auth(bad_token))
    assert r.status_code == 401


# ---- Scan tracking (type="url" only) -------------------------------------

def test_url_code_scan_is_tracked(client):
    token = make_token(tenant_id=400)
    r = client.post("/codes", json={"type": "url", "url": "https://example.com/destination"}, headers=auth(token))
    qr_id = r.json()["id"]

    # get the actual scan_code by inspecting the redirect the image points at -
    # simplest way in a test is to query the DB directly via the app's own session
    from app.database import SessionLocal
    from app.models import QRCode
    db = SessionLocal()
    qr_row = db.query(QRCode).filter(QRCode.id == qr_id).first()
    scan_code = qr_row.scan_code
    db.close()
    assert scan_code  # url types always get one

    r2 = client.get(f"/s/{scan_code}", headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"}, follow_redirects=False)
    assert r2.status_code == 302
    assert r2.headers["location"] == "https://example.com/destination"

    r3 = client.get(f"/codes/{qr_id}/scans", headers=auth(token))
    assert r3.status_code == 200
    assert len(r3.json()) == 1
    assert "Chrome" in r3.json()[0]["browser"]

    r4 = client.get(f"/codes/{qr_id}/stats", headers=auth(token))
    assert r4.status_code == 200
    assert r4.json()["summary"]["total"] == 1


def test_scan_unknown_code_404(client):
    r = client.get("/s/doesnotexist12", follow_redirects=False)
    assert r.status_code == 404


def test_text_type_has_no_scan_code(client):
    token = make_token(tenant_id=401)
    r = client.post("/codes", json={"type": "text", "text": "not trackable"}, headers=auth(token))
    qr_id = r.json()["id"]

    from app.database import SessionLocal
    from app.models import QRCode
    db = SessionLocal()
    qr_row = db.query(QRCode).filter(QRCode.id == qr_id).first()
    assert qr_row.scan_code is None
    db.close()


def test_tenant_stats_endpoint(client):
    token = make_token(tenant_id=402)
    client.post("/codes", json={"type": "url", "url": "https://example.com/a"}, headers=auth(token))
    r = client.get("/stats", headers=auth(token))
    assert r.status_code == 200
    assert "summary" in r.json() and "daily" in r.json()


def test_console_page_loads(client):
    r = client.get("/console")
    assert r.status_code == 200
    assert "Enter your access token" in r.text


def test_console_static_assets_serve(client):
    r = client.get("/static/js/console.js")
    assert r.status_code == 200
    r2 = client.get("/static/js/chart.umd.min.js")
    assert r2.status_code == 200
