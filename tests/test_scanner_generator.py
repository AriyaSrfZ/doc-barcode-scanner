"""
Comprehensive tests for Document & Picture Barcode Scanner and 1D/2D Generator.
"""

from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageOps
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


def test_scan_picture_with_skewed_barcode():
    png_bytes = generator.generate_barcode("code128", "SKEWED-IMG-77", "png")
    img = Image.open(BytesIO(png_bytes)).rotate(45, expand=True, fillcolor="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    files = {"file": ("skewed_label.png", buf.getvalue(), "image/png")}
    res = client.post("/api/v1/scan", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["total_detected"] == 1
    assert data["barcodes"][0]["symbology"] == "CODE128"
    assert data["barcodes"][0]["data"] == "SKEWED-IMG-77"
    assert data["barcodes"][0]["rect"]["width"] > 0
    assert data["barcodes"][0]["rect"]["height"] > 0


def test_scan_pdf_document_with_skewed_barcode():
    png_bytes = generator.generate_barcode("code128", "SKEWED-PDF-88", "png")
    img = Image.open(BytesIO(png_bytes)).rotate(35, expand=True, fillcolor="white").convert("RGB")
    pdf_buf = BytesIO()
    img.save(pdf_buf, format="PDF")
    files = {"file": ("skewed_document.pdf", pdf_buf.getvalue(), "application/pdf")}
    res = client.post("/api/v1/scan", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["total_detected"] >= 1
    assert data["barcodes"][0]["data"] == "SKEWED-PDF-88"
    assert data["barcodes"][0]["page"] == 1


def test_scan_picture_with_multiple_barcodes_at_mixed_angles():
    # 1. Generate one horizontal Code128 and one 45-degree tilted Code128
    b1_bytes = generator.generate_barcode("code128", "HORIZ-CODE-101", "png")
    b2_bytes = generator.generate_barcode("code128", "TILT-CODE-202", "png")
    img1 = Image.open(BytesIO(b1_bytes))
    img2 = Image.open(BytesIO(b2_bytes)).rotate(45, expand=True, fillcolor="white")

    canvas = Image.new("RGB", (img1.width + img2.width + 100, max(img1.height, img2.height) + 100), "white")
    canvas.paste(img1, (20, 20))
    canvas.paste(img2, (img1.width + 50, 20))

    buf = BytesIO()
    canvas.save(buf, format="PNG")
    files = {"file": ("mixed_angles.png", buf.getvalue(), "image/png")}
    res = client.post("/api/v1/scan", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["total_detected"] == 2
    detected_payloads = {b["data"] for b in data["barcodes"]}
    assert "HORIZ-CODE-101" in detected_payloads
    assert "TILT-CODE-202" in detected_payloads


def test_scan_picture_with_multiple_skewed_barcodes():
    # 2. Generate two barcodes with different skew angles (35 deg and 75 deg)
    b1_bytes = generator.generate_barcode("code128", "SKEW-35-DEG", "png")
    b2_bytes = generator.generate_barcode("code128", "SKEW-75-DEG", "png")
    img1 = Image.open(BytesIO(b1_bytes)).rotate(35, expand=True, fillcolor="white")
    img2 = Image.open(BytesIO(b2_bytes)).rotate(75, expand=True, fillcolor="white")

    canvas = Image.new("RGB", (img1.width + img2.width + 100, max(img1.height, img2.height) + 100), "white")
    canvas.paste(img1, (20, 20))
    canvas.paste(img2, (img1.width + 50, 20))

    buf = BytesIO()
    canvas.save(buf, format="PNG")
    files = {"file": ("two_skews.png", buf.getvalue(), "image/png")}
    res = client.post("/api/v1/scan", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["total_detected"] == 2
    detected_payloads = {b["data"] for b in data["barcodes"]}
    assert "SKEW-35-DEG" in detected_payloads
    assert "SKEW-75-DEG" in detected_payloads


def test_scan_picture_with_inverted_barcode():
    # 3. Barcode with inverted polarity (white bars on black background)
    b_bytes = generator.generate_barcode("code128", "INVERTED-WHITE-CODE", "png")
    norm_img = Image.open(BytesIO(b_bytes)).convert("L")
    inv_img = ImageOps.invert(norm_img)

    buf = BytesIO()
    inv_img.save(buf, format="PNG")
    files = {"file": ("inverted.png", buf.getvalue(), "image/png")}
    res = client.post("/api/v1/scan", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["total_detected"] >= 1
    assert data["barcodes"][0]["data"] == "INVERTED-WHITE-CODE"


def test_scan_multipage_pdf_document():
    # 4. Multi-page PDF: Page 1 has Code128, Page 2 has QR code
    b1_bytes = generator.generate_barcode("code128", "PDF-PAGE-1-CODE", "png")
    b2_bytes = generator.generate_barcode("qr", "https://example.com/pdf-page-2", "png")

    img1 = Image.open(BytesIO(b1_bytes)).convert("RGB")
    img2 = Image.open(BytesIO(b2_bytes)).convert("RGB")

    pdf_buf = BytesIO()
    img1.save(pdf_buf, format="PDF", save_all=True, append_images=[img2])

    files = {"file": ("multipage.pdf", pdf_buf.getvalue(), "application/pdf")}
    res = client.post("/api/v1/scan", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["total_detected"] >= 2
    pages = {b["page"] for b in data["barcodes"]}
    payloads = {b["data"] for b in data["barcodes"]}
    assert 1 in pages
    assert 2 in pages
    assert "PDF-PAGE-1-CODE" in payloads
    assert "https://example.com/pdf-page-2" in payloads


def test_generate_empty_data_rejected():
    res = client.post(
        "/api/v1/generate",
        json={"symbology": "code128", "data": "   "},
    )
    assert res.status_code == 400
    assert "cannot be empty" in res.json()["detail"].lower()


def test_generate_invalid_digits_for_ean_rejected():
    # EAN-13 requires digits only; letters must return 400, not 500
    res = client.post(
        "/api/v1/generate",
        json={"symbology": "ean13", "data": "ABCDEFGHIJKLM"},
    )
    assert res.status_code == 400
    assert "number" in res.json()["detail"].lower() or "ean" in res.json()["detail"].lower()


def test_generate_ean8_and_isbn13_png_and_svg():
    # Test EAN-8
    res_ean8_png = client.post(
        "/api/v1/generate",
        json={"symbology": "ean8", "data": "96385074", "output_format": "png"},
    )
    assert res_ean8_png.status_code == 200
    assert res_ean8_png.headers["content-type"] == "image/png"

    res_ean8_svg = client.post(
        "/api/v1/generate",
        json={"symbology": "ean8", "data": "96385074", "output_format": "svg"},
    )
    assert res_ean8_svg.status_code == 200
    assert res_ean8_svg.headers["content-type"] == "image/svg+xml"

    # Test ISBN-13
    res_isbn_png = client.post(
        "/api/v1/generate",
        json={"symbology": "isbn13", "data": "9780306406157", "output_format": "png"},
    )
    assert res_isbn_png.status_code == 200
    assert res_isbn_png.headers["content-type"] == "image/png"


def test_generate_qr_svg_custom_colors():
    res = client.post(
        "/api/v1/generate",
        json={
            "symbology": "qr",
            "data": "https://example.com/colored-svg",
            "output_format": "svg",
            "fg_color": "#ff0000",
            "bg_color": "#00ff00",
        },
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/svg+xml"
    content = res.content.lower()
    assert b"#ff0000" in content or b"#00ff00" in content


def test_scan_encrypted_pdf_rejected_400():
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("securepass")
    buf = BytesIO()
    writer.write(buf)

    files = {"file": ("encrypted_doc.pdf", buf.getvalue(), "application/pdf")}
    res = client.post("/api/v1/scan", files=files)
    assert res.status_code == 400
    assert "encrypted" in res.json()["detail"].lower()


def test_scan_picture_with_exif_orientation():
    # Code128 with EXIF orientation 6 (90 deg CW)
    png_bytes = generator.generate_barcode("code128", "EXIF-TAG-TEST", "png")
    im = Image.open(BytesIO(png_bytes))
    exif = im.getexif()
    exif[274] = 6  # Orientation 6
    buf = BytesIO()
    im.save(buf, format="JPEG", exif=exif)

    files = {"file": ("exif_photo.jpg", buf.getvalue(), "image/jpeg")}
    res = client.post("/api/v1/scan", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["total_detected"] >= 1
    assert data["barcodes"][0]["data"] == "EXIF-TAG-TEST"



