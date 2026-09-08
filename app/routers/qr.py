"""
Two ways to get a QR code:

POST /render - stateless. Give it content, get an image back
  immediately. Nothing is saved. Works with X-API-Key (no tenant
  context needed) or a bearer JWT (tenant context ignored, just used
  as auth). This is the fast path for embedding or one-off use.

POST /codes + GET /codes/... - persisted, tenant-scoped. Requires a
  bearer JWT (from your identity-service). Saved codes show up in
  GET /codes for that tenant only - a JWT from tenant A can never see
  or delete tenant B's codes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud
from app.models import QRCode
from app.schemas import QRRequest, QRCodeOut
from app.deps import require_api_key_or_tenant, require_tenant_claims, Claims
from app import qrgen

router = APIRouter(tags=["qr"])


def _build_content(payload: QRRequest) -> str:
    if payload.type == "url":
        if not payload.url:
            raise ValueError("url is required when type='url'.")
        return payload.url
    if payload.type == "text":
        if not payload.text:
            raise ValueError("text is required when type='text'.")
        return qrgen.build_text_payload(payload.text)
    if payload.type == "wifi":
        if not payload.wifi_ssid:
            raise ValueError("wifi_ssid is required when type='wifi'.")
        return qrgen.build_wifi_payload(payload.wifi_ssid, payload.wifi_password or "", payload.wifi_security or "WPA", bool(payload.wifi_hidden))
    if payload.type == "vcard":
        if not payload.vcard_name:
            raise ValueError("vcard_name is required when type='vcard'.")
        return qrgen.build_vcard_payload(payload.vcard_name, payload.vcard_phone or "", payload.vcard_email or "", payload.vcard_org or "")
    raise ValueError("type must be one of: url, text, wifi, vcard.")


@router.post(
    "/render",
    summary="Generate a QR image immediately, no persistence",
    description="Accepts X-API-Key OR a bearer token. Returns the image directly - nothing is saved.",
    responses={200: {"content": {"image/png": {}, "image/svg+xml": {}}}, 400: {"description": "Invalid input"}, 401: {"description": "Missing/invalid auth"}},
)
def render(payload: QRRequest, _: object = Depends(require_api_key_or_tenant)):
    if not qrgen.is_valid_hex_color(payload.fg_color) or not qrgen.is_valid_hex_color(payload.bg_color):
        raise HTTPException(status_code=400, detail="fg_color/bg_color must be hex like #000000.")
    try:
        content = _build_content(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if payload.format == "svg":
        return Response(content=qrgen.generate_svg(content), media_type="image/svg+xml")
    png = qrgen.generate_png(content, fg_color=payload.fg_color, bg_color=payload.bg_color)
    return Response(content=png, media_type="image/png")


def _to_out(qr: QRCode, base_url: str = "") -> QRCodeOut:
    return QRCodeOut(
        id=qr.id, type=qr.type, fg_color=qr.fg_color, bg_color=qr.bg_color, created_at=qr.created_at,
        image_url=f"/codes/{qr.id}/image", svg_url=f"/codes/{qr.id}/svg",
    )


@router.post("/codes", response_model=QRCodeOut, summary="Generate and save a QR code (tenant-scoped, requires bearer token)")
def create_code(payload: QRRequest, db: Session = Depends(get_db), claims: Claims = Depends(require_tenant_claims)):
    if not qrgen.is_valid_hex_color(payload.fg_color) or not qrgen.is_valid_hex_color(payload.bg_color):
        raise HTTPException(status_code=400, detail="fg_color/bg_color must be hex like #000000.")
    try:
        content = _build_content(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    qr = crud.create_qr_code(
        db, qr_type=payload.type, content=content, tenant_id=claims.tenant_id, owner_user_id=claims.user_id,
        fg_color=payload.fg_color, bg_color=payload.bg_color,
    )
    return _to_out(qr)


@router.get("/codes", response_model=list[QRCodeOut], summary="List this tenant's saved QR codes")
def list_codes(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), claims: Claims = Depends(require_tenant_claims)):
    codes = crud.list_qr_codes_for_tenant(db, claims.tenant_id, skip=skip, limit=limit)
    return [_to_out(c) for c in codes]


@router.delete("/codes/{qr_id}", summary="Delete a saved QR code")
def delete_code(qr_id: int, db: Session = Depends(get_db), claims: Claims = Depends(require_tenant_claims)):
    if not crud.delete_qr_code_for_tenant(db, qr_id, claims.tenant_id):
        raise HTTPException(status_code=404, detail="QR code not found")
    return {"ok": True}


@router.get("/codes/{qr_id}/image", responses={200: {"content": {"image/png": {}}}, 404: {"description": "Not found"}})
def get_code_image(qr_id: int, db: Session = Depends(get_db), claims: Claims = Depends(require_tenant_claims)):
    qr = crud.get_qr_code_for_tenant(db, qr_id, claims.tenant_id)
    if not qr:
        raise HTTPException(status_code=404, detail="QR code not found")
    png = qrgen.generate_png(qr.content, fg_color=qr.fg_color, bg_color=qr.bg_color)
    return Response(content=png, media_type="image/png")


@router.get("/codes/{qr_id}/svg", responses={200: {"content": {"image/svg+xml": {}}}, 404: {"description": "Not found"}})
def get_code_svg(qr_id: int, db: Session = Depends(get_db), claims: Claims = Depends(require_tenant_claims)):
    qr = crud.get_qr_code_for_tenant(db, qr_id, claims.tenant_id)
    if not qr:
        raise HTTPException(status_code=404, detail="QR code not found")
    return Response(content=qrgen.generate_svg(qr.content), media_type="image/svg+xml")
