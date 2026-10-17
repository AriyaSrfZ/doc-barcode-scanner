"""
Comprehensive tests for Document & Picture Barcode Scanner and 1D/2D Generator.
"""

from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import pypdf

from app.main import app
from app import generator, scanner

client = TestClient(app)


def test_list_formats():
    res = client.get("/api/v1/formats")
    assert res.status_code == 200
    data = res.json()
    assert "symbologies" in data
    assert "code128" in [s["id"] for s in data["symbologies"]["1d"]]
    assert "qr" in [s["id"] for s in data["symbologies"]["2d"]]


def test_generate_1d_barcode_png():
    res = client.post(
        "/api/v1/generate",
        json={
            "symbology": "code128",
            "data": "DOC-SAMPLE-99",
            "output_format": "png",
            "fg_color": "#000000",
            "bg_color": "#ffffff",
        },
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert len(res.content) > 100

    # Verify Pillow can open it
    img = Image.open(BytesIO(res.content))
    assert img.size[0] > 0 and img.size[1] > 0


def test_generate_1d_barcode_svg():
    res = client.post(
        "/api/v1/generate",
        json={
            "symbology": "code128",
            "data": "INVOICE-1234",
            "output_format": "svg",
        },
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/svg+xml"
    assert b"<svg" in res.content


def test_generate_qr_code_png_and_svg():
    res_png = client.post(
        "/api/v1/generate",
        json={"symbology": "qr", "data": "https://example.com", "output_format": "png"},
    )
    assert res_png.status_code == 200
    assert res_png.headers["content-type"] == "image/png"

    res_svg = client.post(
        "/api/v1/generate",
        json={"symbology": "qr", "data": "https://example.com", "output_format": "svg"},
    )
    assert res_svg.status_code == 200
    assert res_svg.headers["content-type"] == "image/svg+xml"


def test_scan_picture_with_barcode():
    # 1. Generate a Code128 image
    png_bytes = generator.generate_barcode("code128", "SCAN-ME-8822", "png")

    # 2. Upload and scan it
    files = {"file": ("test_label.png", png_bytes, "image/png")}
    res = client.post("/api/v1/scan", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["total_detected"] == 1
    assert data["barcodes"][0]["symbology"] == "CODE128"
    assert data["barcodes"][0]["data"] == "SCAN-ME-8822"
    assert data["barcodes"][0]["rect"]["width"] > 0


def test_scan_picture_with_qr_code():
    png_bytes = generator.generate_barcode("qr", "https://example.com/item/42", "png")
    files = {"file": ("qrcode.png", png_bytes, "image/png")}
    res = client.post("/api/v1/scan", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["total_detected"] == 1
    assert data["barcodes"][0]["symbology"] == "QRCODE"
    assert data["barcodes"][0]["data"] == "https://example.com/item/42"


def test_scan_pdf_document_with_barcode():
    # 1. Generate barcode image
    png_bytes = generator.generate_barcode("code128", "PDF-BARCODE-55", "png")
    img = Image.open(BytesIO(png_bytes)).convert("RGB")

    # 2. Wrap into a PDF
    pdf_buf = BytesIO()
    img.save(pdf_buf, format="PDF")
    pdf_buf.seek(0)

    # 3. Upload PDF and scan
    files = {"file": ("document_with_barcode.pdf", pdf_buf.getvalue(), "application/pdf")}
    res = client.post("/api/v1/scan", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["total_detected"] >= 1
    assert data["barcodes"][0]["data"] == "PDF-BARCODE-55"
    assert data["barcodes"][0]["page"] == 1


def test_generate_invalid_color_rejected():
    res = client.post(
        "/api/v1/generate",
        json={"symbology": "qr", "data": "test", "fg_color": "not-a-color"},
    )
    assert res.status_code == 400


def test_generate_invalid_symbology_rejected():
    res = client.post(
        "/api/v1/generate",
        json={"symbology": "nonexistent_code", "data": "test"},
    )
    assert res.status_code == 400
