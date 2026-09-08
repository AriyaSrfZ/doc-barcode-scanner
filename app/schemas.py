from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class QRRequest(BaseModel):
    """Shared shape for both /render (stateless) and /codes (persisted)."""
    type: str = Field(..., description="One of: url, text, wifi, vcard.", examples=["url"])
    url: Optional[str] = Field(None, description="Required when type='url'. Any URL - this service doesn't care where it came from.")
    text: Optional[str] = Field(None, description="Required when type='text'.")
    wifi_ssid: Optional[str] = Field(None, description="Required when type='wifi'.")
    wifi_password: Optional[str] = None
    wifi_security: Optional[str] = Field("WPA", description="WPA, WEP, or nopass.")
    wifi_hidden: Optional[bool] = False
    vcard_name: Optional[str] = Field(None, description="Required when type='vcard'.")
    vcard_phone: Optional[str] = None
    vcard_email: Optional[str] = None
    vcard_org: Optional[str] = None
    fg_color: str = Field("#000000", description="Hex color. PNG only.")
    bg_color: str = Field("#ffffff", description="Hex color. PNG only.")
    format: str = Field("png", description="png or svg. Only used by /render (/codes always serves both via separate endpoints).")


class QRCodeOut(BaseModel):
    id: int
    type: str
    fg_color: str
    bg_color: str
    created_at: datetime
    image_url: str
    svg_url: str

    model_config = {"from_attributes": True}
