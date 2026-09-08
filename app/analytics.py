"""
Aggregate scan analytics for a QR code. Same shape and logic as
link-shortener's analytics.py (clicks_per_day, top devices/countries) -
scans are the QR-equivalent of clicks, so the same queries apply,
just against QRScan instead of Click.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import QRScan, QRCode


def _base_query(db: Session, *columns, qr_code_id: Optional[int], tenant_id: Optional[int]):
    query = db.query(*columns)
    if tenant_id is not None:
        query = query.join(QRCode, QRScan.qr_code_id == QRCode.id).filter(QRCode.tenant_id == tenant_id)
    if qr_code_id is not None:
        query = query.filter(QRScan.qr_code_id == qr_code_id)
    return query


def scans_per_day(db: Session, qr_code_id: Optional[int] = None, tenant_id: Optional[int] = None, days: int = 14) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days - 1)
    since = since.replace(hour=0, minute=0, second=0, microsecond=0)

    query = _base_query(
        db, func.date(QRScan.scanned_at).label("day"), func.count(QRScan.id).label("count"),
        qr_code_id=qr_code_id, tenant_id=tenant_id,
    ).filter(QRScan.scanned_at >= since)

    rows = {r.day: r.count for r in query.group_by("day").all()}
    result = []
    for i in range(days):
        day = (since + timedelta(days=i)).date()
        key = day.isoformat()
        result.append({"day": key, "count": rows.get(key, 0)})
    return result


def device_breakdown(db: Session, qr_code_id: Optional[int] = None, tenant_id: Optional[int] = None) -> list[dict]:
    query = _base_query(db, QRScan.device_type, func.count(QRScan.id).label("count"), qr_code_id=qr_code_id, tenant_id=tenant_id)
    rows = query.group_by(QRScan.device_type).order_by(func.count(QRScan.id).desc()).all()
    return [{"device_type": r.device_type or "unknown", "count": r.count} for r in rows]


def top_countries(db: Session, qr_code_id: Optional[int] = None, tenant_id: Optional[int] = None, limit: int = 5) -> list[dict]:
    query = _base_query(db, QRScan.country, func.count(QRScan.id).label("count"), qr_code_id=qr_code_id, tenant_id=tenant_id)
    rows = query.group_by(QRScan.country).order_by(func.count(QRScan.id).desc()).limit(limit).all()
    return [{"country": r.country or "Unknown", "count": r.count} for r in rows]


def total_scans_summary(db: Session, qr_code_id: Optional[int] = None, tenant_id: Optional[int] = None) -> dict:
    total = _base_query(db, func.count(QRScan.id), qr_code_id=qr_code_id, tenant_id=tenant_id).scalar() or 0
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    last_24h = (
        _base_query(db, func.count(QRScan.id), qr_code_id=qr_code_id, tenant_id=tenant_id)
        .filter(QRScan.scanned_at >= since_24h)
        .scalar()
        or 0
    )
    return {"total": total, "last_24h": last_24h}
