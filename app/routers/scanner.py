"""
Barcode & Document Scanner and Generator API Router.
"""

from typing import List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from app import generator, scanner

router = APIRouter(prefix="/api/v1", tags=["scanner-generator"])


class BarcodeRectModel(BaseModel):
    x: int
    y: int
    width: int
    height: int


class DetectedBarcodeModel(BaseModel):
    symbology: str
    data: str
    page: int
    rect: BarcodeRectModel


class ScanResponse(BaseModel):
    filename: str
    total_detected: int
    barcodes: List[DetectedBarcodeModel]


class GenerateRequest(BaseModel):
    symbology: str = Field("qr", description="Symbology: qr, code128, code39, ean13, ean8, upca, isbn13")
    data: str = Field(..., description="String payload to encode")
    output_format: str = Field("png", description="Output format: png or svg")
    fg_color: str = Field("#000000", description="Foreground hex color, e.g. #000000")
    bg_color: str = Field("#ffffff", description="Background hex color, e.g. #ffffff")


@router.get("/formats", summary="List supported barcode and QR symbologies")
def list_formats():
    return {
        "symbologies": {
            "2d": [
                {"id": "qr", "name": "QR Code", "description": "High-capacity 2D matrix code for URLs, contact cards, WiFi"}
            ],
            "1d": [
                {"id": "code128", "name": "Code 128", "description": "High-density alphanumeric barcode widely used in logistics"},
                {"id": "code39", "name": "Code 39", "description": "Variable-length alphanumeric barcode standard"},
                {"id": "ean13", "name": "EAN-13", "description": "13-digit European Article Number for retail products"},
                {"id": "ean8", "name": "EAN-8", "description": "8-digit compact retail barcode"},
                {"id": "upca", "name": "UPC-A", "description": "12-digit Universal Product Code standard"},
                {"id": "isbn13", "name": "ISBN-13", "description": "13-digit International Standard Book Number"},
            ]
        },
        "output_formats": ["png", "svg"],
        "input_formats": ["png", "jpg", "jpeg", "webp", "bmp", "pdf"]
    }


@router.post(
    "/scan",
    response_model=ScanResponse,
    summary="Scan picture or document for barcodes and QR codes",
    description="Upload an image (PNG, JPG, WebP) or PDF document. Scans and decodes all barcodes found with bounding boxes.",
)
async def scan_file_endpoint(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        detected = scanner.scan_file(content, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scanning failed: {exc}")

    barcodes_out = [
        DetectedBarcodeModel(
            symbology=b.symbology,
            data=b.data,
            page=b.page,
            rect=BarcodeRectModel(**b.rect.to_dict()),
        )
        for b in detected
    ]

    return ScanResponse(
        filename=file.filename,
        total_detected=len(barcodes_out),
        barcodes=barcodes_out,
    )


@router.post(
    "/generate",
    summary="Generate 1D barcode or 2D QR code",
    description="Generates a barcode image in PNG or SVG format.",
)
def generate_barcode_endpoint(payload: GenerateRequest):
    if not generator.is_valid_hex_color(payload.fg_color) or not generator.is_valid_hex_color(payload.bg_color):
        raise HTTPException(status_code=400, detail="fg_color and bg_color must be 6-digit hex like #000000.")

    try:
        img_bytes = generator.generate_barcode(
            symbology=payload.symbology,
            data=payload.data,
            output_format=payload.output_format,
            fg_color=payload.fg_color,
            bg_color=payload.bg_color,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}")

    media_type = "image/svg+xml" if payload.output_format.lower() == "svg" else "image/png"
    return Response(content=img_bytes, media_type=media_type)
