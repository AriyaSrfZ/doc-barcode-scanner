from typing import Optional

from sqlalchemy.orm import Session

from app.models import QRCode


def create_qr_code(
    db: Session, qr_type: str, content: str, tenant_id: Optional[int], owner_user_id: Optional[int],
    fg_color: str = "#000000", bg_color: str = "#ffffff", scan_code: Optional[str] = None,
) -> QRCode:
    qr = QRCode(
        type=qr_type, content=content, tenant_id=tenant_id, owner_user_id=owner_user_id,
        fg_color=fg_color, bg_color=bg_color, scan_code=scan_code,
    )
    db.add(qr)
    db.commit()
    db.refresh(qr)
    return qr


def get_qr_code_by_id(db: Session, qr_id: int) -> Optional[QRCode]:
    return db.query(QRCode).filter(QRCode.id == qr_id).first()


def get_qr_code_for_tenant(db: Session, qr_id: int, tenant_id: int) -> Optional[QRCode]:
    qr = get_qr_code_by_id(db, qr_id)
    if qr and qr.tenant_id == tenant_id:
        return qr
    return None


def list_qr_codes_for_tenant(db: Session, tenant_id: int, skip: int = 0, limit: int = 100):
    return (
        db.query(QRCode)
        .filter(QRCode.tenant_id == tenant_id)
        .order_by(QRCode.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def delete_qr_code_for_tenant(db: Session, qr_id: int, tenant_id: int) -> bool:
    qr = get_qr_code_for_tenant(db, qr_id, tenant_id)
    if not qr:
        return False
    db.delete(qr)
    db.commit()
    return True


def get_qr_code_by_scan_code(db: Session, scan_code: str) -> Optional[QRCode]:
    return db.query(QRCode).filter(QRCode.scan_code == scan_code).first()


def log_scan(db: Session, qr_code_id: int, ip_address, referrer, user_agent_raw):
    from app.useragent import parse_user_agent
    from app.geoip import lookup_country
    from app.models import QRScan

    ua_info = parse_user_agent(user_agent_raw or "")
    geo_info = lookup_country(ip_address or "")
    scan = QRScan(
        qr_code_id=qr_code_id, ip_address=ip_address, referrer=referrer,
        browser=ua_info["browser"], os=ua_info["os"], device_type=ua_info["device_type"],
        country=geo_info["country"],
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def count_scans(db: Session, qr_code_id: int) -> int:
    from app.models import QRScan
    from sqlalchemy import func
    return db.query(func.count(QRScan.id)).filter(QRScan.qr_code_id == qr_code_id).scalar() or 0
