"""
Central configuration. This service is deliberately identity-agnostic:
it doesn't have its own user table. Auth is either a bearer JWT (verified
against an external identity service's public key) or a local API key
for simple stateless use with no tenant/user context at all.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/qr.db")

    # Simple server-to-server key for stateless rendering (no tenant
    # context needed - see POST /render vs POST /codes in docs/API.md).
    api_key: str = os.getenv("API_KEY", "")

    # Identity service integration (optional - only needed for the
    # persisted, tenant-scoped /codes endpoints).
    identity_public_key_url: str = os.getenv("IDENTITY_PUBLIC_KEY_URL", "")
    # Alternative to the URL above: paste the PEM directly (useful when
    # this service can't reach identity-service over the network at
    # startup, e.g. air-gapped deployments). URL takes priority if both are set.
    identity_public_key_pem: str = os.getenv("IDENTITY_PUBLIC_KEY_PEM", "")
    jwt_issuer: str = os.getenv("JWT_ISSUER", "identity-service")


settings = Settings()
