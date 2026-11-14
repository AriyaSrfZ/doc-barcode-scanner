"""
1D and 2D Barcode & QR Code Generation Engine.
Supports Code128, EAN-13, EAN-8, Code39, UPC-A, and QR Codes with PNG and SVG output.
"""

import re
from io import BytesIO
from typing import Optional

import barcode
from barcode.writer import ImageWriter, SVGWriter
import qrcode
import qrcode.image.svg
from qrcode.constants import ERROR_CORRECT_M

HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")

SUPPORTED_1D_FORMATS = {
    "code128": "code128",
    "code39": "code39",
    "ean13": "ean13",
    "ean8": "ean8",
    "upca": "upca",
    "isbn13": "isbn13",
}

SUPPORTED_2D_FORMATS = {
    "qr": "qr",
    "qrcode": "qr",
}


def is_valid_hex_color(value: str) -> bool:
    return bool(HEX_COLOR_PATTERN.match(value))


def _escape_vcard(value: str) -> str:
    return value.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")


def build_text_payload(text: str) -> str:
    return text.strip()


def build_wifi_payload(ssid: str, password: str, security: str = "WPA", hidden: bool = False) -> str:
    """Standard WIFI: URI format recognized by mobile scanners."""
    security = security.upper() if security.upper() in ("WPA", "WEP") else "nopass"
    ssid_esc = ssid.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace(":", "\\:")
    pwd_esc = "" if security == "nopass" else password.replace("\\", "\\\\").replace(";", "\\;")
    hidden_str = "true" if hidden else "false"
    return f"WIFI:T:{security};S:{ssid_esc};P:{pwd_esc};H:{hidden_str};;"


def build_vcard_payload(name: str, phone: str = "", email: str = "", org: str = "") -> str:
    """vCard 3.0 format for QR contact cards."""
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"N:;{_escape_vcard(name)};;;", f"FN:{_escape_vcard(name)}"]
    if org:
        lines.append(f"ORG:{_escape_vcard(org)}")
    if phone:
        lines.append(f"TEL:{_escape_vcard(phone)}")
    if email:
        lines.append(f"EMAIL:{_escape_vcard(email)}")
    lines.append("END:VCARD")
    return "\n".join(lines)


def generate_barcode(
    symbology: str,
    data: str,
    output_format: str = "png",
    fg_color: str = "#000000",
    bg_color: str = "#ffffff",
) -> bytes:
    """
    Generate either a 1D barcode or 2D QR code.
    Returns raw bytes of PNG or SVG.
    """
    if not data or not data.strip():
        raise ValueError("Data payload cannot be empty.")

    sym = symbology.lower().strip()
    fmt = output_format.lower().strip()

    if sym in SUPPORTED_2D_FORMATS:
        return _generate_qr(data, fmt, fg_color, bg_color)

    if sym in SUPPORTED_1D_FORMATS:
        return _generate_1d_barcode(sym, data, fmt, fg_color, bg_color)

    raise ValueError(
        f"Unsupported symbology '{symbology}'. Supported: {list(SUPPORTED_1D_FORMATS.keys()) + ['qr']}"
    )


def _generate_qr(
    data: str,
    output_format: str = "png",
    fg_color: str = "#000000",
    bg_color: str = "#ffffff",
    box_size: int = 10,
    border: int = 4,
) -> bytes:
    if output_format == "svg":
        qr = qrcode.QRCode(
            image_factory=qrcode.image.svg.SvgPathImage,
            error_correction=ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color=fg_color, back_color=bg_color)
        buf = BytesIO()
        img.save(buf)
        return buf.getvalue()

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=box_size, border=border)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fg_color, back_color=bg_color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _generate_1d_barcode(
    symbology: str,
    data: str,
    output_format: str = "png",
    fg_color: str = "#000000",
    bg_color: str = "#ffffff",
) -> bytes:
    writer_class = SVGWriter if output_format == "svg" else ImageWriter
    writer = writer_class()
    
    # Configure writer colors if supported
    writer_options = {
        "module_width": 0.3,
        "module_height": 15.0,
        "quiet_zone": 6.5,
        "font_size": 10,
        "text_distance": 5.0,
        "background": bg_color,
        "foreground": fg_color,
    }

    try:
        barcode_class = barcode.get_barcode_class(SUPPORTED_1D_FORMATS[symbology])
        bc = barcode_class(data, writer=writer)
        buf = BytesIO()
        bc.write(buf, options=writer_options)
        return buf.getvalue()
    except barcode.errors.BarcodeError as exc:
        raise ValueError(str(exc))
