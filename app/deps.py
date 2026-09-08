"""
Two auth paths, deliberately asymmetric in what they allow:

1. Bearer JWT, verified against an external identity-service's public
   key - fetched once and cached in memory (or configured directly via
   IDENTITY_PUBLIC_KEY_PEM for air-gapped setups with no network path
   to identity-service at runtime). Gives tenant_id + user_id + role,
   so persisted QR codes (POST /codes) can be scoped and listed later.

2. X-API-Key - a single shared secret, no tenant/user context at all.
   Only allowed on the stateless POST /render endpoint, which returns
   an image directly and never writes to the database - there is
   nothing to "own" that would need a tenant_id. This is the fast path
   for a caller that just wants an image right now (e.g. an <img> tag
   or a quick script), no identity-service integration required.
"""

from dataclasses import dataclass
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)

_cached_public_key: Optional[str] = None


def _get_public_key() -> Optional[str]:
    global _cached_public_key
    if settings.identity_public_key_pem:
        return settings.identity_public_key_pem
    if _cached_public_key:
        return _cached_public_key
    if not settings.identity_public_key_url:
        return None
    try:
        resp = httpx.get(settings.identity_public_key_url, timeout=5.0)
        resp.raise_for_status()
        _cached_public_key = resp.text
        return _cached_public_key
    except httpx.HTTPError:
        return None


@dataclass
class Claims:
    user_id: Optional[int]
    tenant_id: Optional[int]
    role: Optional[str]


def get_tenant_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[Claims]:
    """For the tenant-scoped /codes endpoints. Returns None if there's no
    valid token - callers decide whether that's a 401."""
    if not credentials:
        return None
    public_key = _get_public_key()
    if not public_key:
        return None
    try:
        payload = jwt.decode(credentials.credentials, public_key, algorithms=["RS256"], issuer=settings.jwt_issuer)
    except JWTError:
        return None
    return Claims(user_id=int(payload["sub"]), tenant_id=payload.get("tenant_id"), role=payload.get("role"))


def require_tenant_claims(claims: Optional[Claims] = Depends(get_tenant_claims)) -> Claims:
    if claims is None:
        raise HTTPException(status_code=401, detail="Valid bearer token required (from your identity service).")
    return claims


def require_api_key_or_tenant(
    x_api_key: Optional[str] = Header(None),
    claims: Optional[Claims] = Depends(get_tenant_claims),
):
    """For POST /render: accepts EITHER a plain API key OR a tenant JWT.
    Returns the Claims if a JWT was used, or None if it was the API key -
    callers can check which happened if it matters."""
    if settings.api_key and x_api_key == settings.api_key:
        return None
    if claims:
        return claims
    raise HTTPException(status_code=401, detail="X-API-Key header or a valid bearer token required.")
