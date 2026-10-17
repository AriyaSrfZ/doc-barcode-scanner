# Document & Picture Barcode Scanner & Generator

A high-performance service for scanning, detecting, and decoding barcodes from pictures and multi-page PDF documents, paired with a dual 1D/2D barcode generator and interactive web studio.

## Features

### 1. Document & Picture Barcode Scanner
- **Multi-Format Ingestion**: Scans PNG, JPG, JPEG, WebP, BMP images and multi-page PDF documents.
- **Deep Barcode Decoding**: Automatically detects and decodes 1D barcodes (`Code 128`, `Code 39`, `EAN-13`, `EAN-8`, `UPC-A`) and 2D matrix codes (`QR Code`).
- **Spatial Localization**: Returns exact bounding box coordinates `(x, y, width, height)` and polygon points for every detected code.
- **Interactive Visual Overlay**: Built-in HTML5 Canvas studio draws bounding boxes and decoded labels directly on uploaded document previews.

### 2. 1D & 2D Barcode Generator
- **Supported 1D Symbologies**: Code 128, Code 39, EAN-13, EAN-8, UPC-A, ISBN-13.
- **Supported 2D Symbologies**: QR Code with automatic formatters for URLs, Plain Text, WiFi configuration, and vCard 3.0 contact cards.
- **Dual Vector & Raster Output**: Export immediately as scalable SVG or high-resolution PNG.
- **Customizable Styling**: Configurable foreground/background hex colors, quiet zones, and module scaling.

### 3. Web Studio & REST API
- **Interactive Web Studio** at `/console`: Drag & drop image/PDF scanner, live visual preview, one-click copy, and instant generator.
- **RESTful Endpoints**: Seamless integration into automated document processing pipelines.

## Quick Start

### Installation

Requires `libzbar0` installed on your system (e.g. `sudo apt install libzbar0` on Debian/Ubuntu).

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/console` to use the interactive studio.

## API Reference

### Scan Image or Document

```http
POST /api/v1/scan
Content-Type: multipart/form-data
```

**Response**:
```json
{
  "filename": "invoice_sample.pdf",
  "total_detected": 1,
  "barcodes": [
    {
      "symbology": "CODE128",
      "data": "INV-2026-9812",
      "page": 1,
      "rect": {
        "x": 140,
        "y": 420,
        "width": 310,
        "height": 75
      }
    }
  ]
}
```

### Generate Barcode

```http
POST /api/v1/generate
Content-Type: application/json

{
  "symbology": "code128",
  "data": "DOC-SERIAL-4421",
  "output_format": "png",
  "fg_color": "#000000",
  "bg_color": "#ffffff"
}
```

Returns binary `image/png` or `image/svg+xml`.

### List Supported Formats

```http
GET /api/v1/formats
```

## Tech Stack

- **Backend**: FastAPI (Python 3.13)
- **Computer Vision & Decoding**: `pyzbar` (ZBar C engine) + `Pillow`
- **Document Extraction**: `pypdf`
- **Barcode Rendering**: `python-barcode` + `qrcode`
- **Frontend Studio**: Vanilla JS + HTML5 Canvas (zero build step)
- **Testing**: `pytest` (27 automated tests)

## Running Tests

```bash
pytest tests/
```
