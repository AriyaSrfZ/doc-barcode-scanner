"""
QRCode: a persisted, generated code. Deliberately has NO foreign key to
any other service's data - `content` is always the literal string this
service will encode, built by the caller (or by this service's own
payload builders for wifi/vcard). This is what makes the service
reusable: it never needs to know about a "Link" table or any other
app's internal IDs.

tenant_id/owner_user_id come from a verified JWT when using the
tenant-scoped /codes endpoints. Both are null for codes created via the
stateless API-key path, which also never persists anything (see
routers/qr.py: POST /render vs POST /codes).
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, Text

from app.database import Base


class QRCode(Base):
    __tablename__ = "qr_codes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=True, index=True)
    owner_user_id = Column(Integer, nullable=True, index=True)

    type = Column(String(20), nullable=False)  # "url", "text", "wifi", "vcard"
    content = Column(Text, nullable=False)  # the literal string this QR encodes

    fg_color = Column(String(9), default="#000000", nullable=False)
    bg_color = Column(String(9), default="#ffffff", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
