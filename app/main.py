"""
Document & Picture Barcode Scanner & Generator Service.
Run locally with: uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import qr, console, scanner

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Document & Picture Barcode Scanner & Generator",
    description="Dual-engine service for decoding barcodes from images/PDFs and generating 1D/2D barcodes.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/console", status_code=303)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.include_router(scanner.router)
app.include_router(qr.router)
app.include_router(console.router)
