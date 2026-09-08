import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("API_KEY", "test-api-key-123")
os.environ.setdefault("JWT_ISSUER", "identity-service")
