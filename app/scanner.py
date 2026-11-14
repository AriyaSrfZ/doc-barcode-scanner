"""
Document and Image Barcode & QR Scanner.
Extracts and decodes 1D barcodes and 2D QR codes from uploaded images and PDF documents.
"""

from dataclasses import dataclass
from io import BytesIO
import math
from typing import List, Optional, Tuple
from PIL import Image, ImageOps
import pyzbar.pyzbar as pyzbar
import pypdf


@dataclass
class BarcodeRect:
    left: int
    top: int
    width: int
    height: int

    def to_dict(self):
        return {
            "x": self.left,
            "y": self.top,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class DetectedBarcode:
    symbology: str
    data: str
    page: int
    rect: BarcodeRect

    def to_dict(self):
        return {
            "symbology": self.symbology,
            "data": self.data,
            "page": self.page,
            "rect": self.rect.to_dict(),
        }


def _unrotate_point(x: float, y: float, angle_deg: float, w_orig: float, h_orig: float, w_rot: float, h_rot: float) -> Tuple[float, float]:
    rad = math.radians(angle_deg)
    dx = x - (w_rot / 2.0)
    dy = y - (h_rot / 2.0)
    x_rel = dx * math.cos(rad) - dy * math.sin(rad)
    y_rel = dx * math.sin(rad) + dy * math.cos(rad)
    return x_rel + (w_orig / 2.0), y_rel + (h_orig / 2.0)


def _is_duplicate_barcode(b1: DetectedBarcode, b2: DetectedBarcode) -> bool:
    if b1.page != b2.page or b1.symbology != b2.symbology or b1.data != b2.data:
        return False
    r1, r2 = b1.rect, b2.rect
    # Check bounding box intersection
    iw = max(0, min(r1.left + r1.width, r2.left + r2.width) - max(r1.left, r2.left))
    ih = max(0, min(r1.top + r1.height, r2.top + r2.height) - max(r1.top, r2.top))
    if (iw * ih) > 0:
        return True
    cx1 = r1.left + r1.width / 2.0
    cy1 = r1.top + r1.height / 2.0
    cx2 = r2.left + r2.width / 2.0
    cy2 = r2.top + r2.height / 2.0
    dist = math.hypot(cx1 - cx2, cy1 - cy2)
    max_dim = max(r1.width, r1.height, r2.width, r2.height)
    return dist <= max(25.0, 0.3 * max_dim)


def _add_barcode_if_unique(results: List[DetectedBarcode], new_bc: DetectedBarcode) -> None:
    for existing in results:
        if _is_duplicate_barcode(existing, new_bc):
            return
    results.append(new_bc)


def scan_image_bytes(image_bytes: bytes, page: int = 1) -> List[DetectedBarcode]:
    """
    Decodes all 1D barcodes and 2D QR codes found within an image byte stream.
    Supports multi-barcode multi-angle detection, automatic orientation correction
    for skewed or rotated scans, and inverted color polarity decoding.
    """
    try:
        img = Image.open(BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img) or img
    except Exception as exc:
        raise ValueError(f"Unable to parse image data: {exc}")

    # Ensure RGB or Grayscale for optimal barcode decoding
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    results: List[DetectedBarcode] = []
    w_orig, h_orig = img.size

    def _process_decoded_objects(decoded_objects, angle_deg: float = 0.0, w_rot: float = 0.0, h_rot: float = 0.0):
        for obj in decoded_objects:
            try:
                payload = obj.data.decode("utf-8")
            except UnicodeDecodeError:
                payload = obj.data.decode("latin-1", errors="replace")

            if angle_deg != 0.0:
                pts = [(p.x, p.y) for p in obj.polygon] if obj.polygon else [
                    (obj.rect.left, obj.rect.top),
                    (obj.rect.left + obj.rect.width, obj.rect.top),
                    (obj.rect.left + obj.rect.width, obj.rect.top + obj.rect.height),
                    (obj.rect.left, obj.rect.top + obj.rect.height),
                ]
                unrotated = [_unrotate_point(px, py, angle_deg, w_orig, h_orig, w_rot, h_rot) for px, py in pts]
                xs = [p[0] for p in unrotated]
                ys = [p[1] for p in unrotated]
                min_x = max(0, int(round(min(xs))))
                min_y = max(0, int(round(min(ys))))
                max_x = min(w_orig, int(round(max(xs))))
                max_y = min(h_orig, int(round(max(ys))))
                rect = BarcodeRect(left=min_x, top=min_y, width=max(1, max_x - min_x), height=max(1, max_y - min_y))
            else:
                r = obj.rect
                rect = BarcodeRect(left=r.left, top=r.top, width=r.width, height=r.height)

            _add_barcode_if_unique(
                results,
                DetectedBarcode(
                    symbology=obj.type,
                    data=payload,
                    page=page,
                    rect=rect,
                ),
            )

    # 1. Direct standard orientation (0 degrees)
    _process_decoded_objects(pyzbar.decode(img))

    # 2. Candidate rotation angles for skewed barcodes
    candidate_angles = (45, 30, 60, 15, 75)
    for angle in candidate_angles:
        rot_img = img.rotate(angle, expand=True, fillcolor="white")
        rot_decoded = pyzbar.decode(rot_img)
        if rot_decoded:
            _process_decoded_objects(rot_decoded, angle_deg=float(angle), w_rot=float(rot_img.width), h_rot=float(rot_img.height))

    # 3. Inverted color polarity (white bars on black background / dark theme)
    inv_img = ImageOps.invert(img.convert("L")).convert("RGB")
    inv_decoded = pyzbar.decode(inv_img)
    if inv_decoded:
        _process_decoded_objects(inv_decoded)
    for angle in candidate_angles:
        rot_inv = inv_img.rotate(angle, expand=True, fillcolor="white")
        rot_inv_dec = pyzbar.decode(rot_inv)
        if rot_inv_dec:
            _process_decoded_objects(rot_inv_dec, angle_deg=float(angle), w_rot=float(rot_inv.width), h_rot=float(rot_inv.height))

    return results


def scan_pdf_bytes(pdf_bytes: bytes) -> List[DetectedBarcode]:
    """
    Extracts embedded page images from a PDF document and scans each for barcodes.
    """
    try:
        reader = pypdf.PdfReader(BytesIO(pdf_bytes))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                pass
            if reader.is_encrypted:
                raise ValueError("PDF document is encrypted or password-protected.")
        pages_list = list(reader.pages)
        if len(pages_list) == 0:
            return []
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Unable to parse PDF document: {exc}")

    results: List[DetectedBarcode] = []

    for page_idx, page in enumerate(pages_list):
        page_num = page_idx + 1
        try:
            images = page.images
        except Exception:
            continue
        for img_obj in images:
            try:
                page_results = scan_image_bytes(img_obj.data, page=page_num)
                for b in page_results:
                    _add_barcode_if_unique(results, b)
            except Exception:
                continue

    return results


def scan_file(file_bytes: bytes, filename: str) -> List[DetectedBarcode]:
    """
    Unified entrypoint: auto-detects PDF vs standard images and extracts barcodes.
    """
    lower_name = filename.lower()
    is_pdf = lower_name.endswith(".pdf") or file_bytes.startswith(b"%PDF")

    if is_pdf:
        return scan_pdf_bytes(file_bytes)
    return scan_image_bytes(file_bytes, page=1)
