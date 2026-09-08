"""
QRCode: a persisted, generated code. `content` is the literal string
this service will encode for text/wifi/vcard types, and is the real
destination for type="url" - but for "url" type, the QR image itself
encodes a *tracking redirect* (GET /s/{scan_code}), not `content`
directly. That's what makes it a genuinely "dynamic" trackable QR code
(the industry-standard pattern), not just a static image: every scan
passes through this service and gets logged before redirecting, the
same way link-shortener already tracks link clicks. Non-URL types have
nothing to redirect through, so they're never trackable - consistent
with how every competing QR platform works (only URL/dynamic codes
carry analytics; text/wifi/vcard are inherently static).

tenant_id/owner_user_id come from a verified JWT via the tenant-scoped
/codes endpoints. Both are null for the stateless /render path, which
never persists anything at all.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class QRCode(Base):
    __tablename__ = "qr_codes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=True, index=True)
    owner_user_id = Column(Integer, nullable=True, index=True)

    type = Column(String(20), nullable=False)  # "url", "text", "wifi", "vcard"
    content = Column(Text, nullable=False)  # literal payload, or the real destination for type="url"

    # Only set for type="url" - the public, unguessable identifier used
    # in the tracking redirect URL (GET /s/{scan_code}). Random, not the
    # sequential DB id, so codes can't be enumerated.
    scan_code = Column(String(16), unique=True, index=True, nullable=True)

    fg_color = Column(String(9), default="#000000", nullable=False)
    bg_color = Column(String(9), default="#ffffff", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    scans = relationship("QRScan", back_populates="qr_code", cascade="all, delete-orphan")


class QRScan(Base):
    """One row per scan of a type='url' QR code - the QR equivalent of
    link-shortener's Click model, same backtrace fields."""
    __tablename__ = "qr_scans"

    id = Column(Integer, primary_key=True, index=True)
    qr_code_id = Column(Integer, ForeignKey("qr_codes.id"), nullable=False, index=True)

    scanned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    ip_address = Column(String(64), nullable=True)
    referrer = Column(Text, nullable=True)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    device_type = Column(String(50), nullable=True)
    country = Column(String(100), nullable=True)

    qr_code = relationship("QRCode", back_populates="scans")
