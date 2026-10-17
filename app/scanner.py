"""
Document and Image Barcode & QR Scanner.
Extracts and decodes 1D barcodes and 2D QR codes from uploaded images and PDF documents.
"""

from dataclasses import dataclass
from io import BytesIO
from typing import List, Optional
from PIL import Image
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


def scan_image_bytes(image_bytes: bytes, page: int = 1) -> List[DetectedBarcode]:
    """
    Decodes all 1D barcodes and 2D QR codes found within an image byte stream.
    """
    try:
        img = Image.open(BytesIO(image_bytes))
    except Exception as exc:
        raise ValueError(f"Unable to parse image data: {exc}")

    # Ensure RGB or Grayscale for optimal barcode decoding
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    decoded_objects = pyzbar.decode(img)
    results: List[DetectedBarcode] = []

    for obj in decoded_objects:
        try:
            payload = obj.data.decode("utf-8")
        except UnicodeDecodeError:
            payload = obj.data.decode("latin-1", errors="replace")

        r = obj.rect
        results.append(
            DetectedBarcode(
                symbology=obj.type,
                data=payload,
                page=page,
                rect=BarcodeRect(left=r.left, top=r.top, width=r.width, height=r.height),
            )
        )

    return results


def scan_pdf_bytes(pdf_bytes: bytes) -> List[DetectedBarcode]:
    """
    Extracts embedded page images from a PDF document and scans each for barcodes.
    """
    try:
        reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    except Exception as exc:
        raise ValueError(f"Unable to parse PDF document: {exc}")

    results: List[DetectedBarcode] = []

    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        for img_obj in page.images:
            try:
                page_results = scan_image_bytes(img_obj.data, page=page_num)
                results.extend(page_results)
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
