"""
Run locally with: uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import qr, console

Base.metadata.create_all(bind=engine)

app = FastAPI(title="QR Generator Service", version="0.2.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.include_router(qr.router)
app.include_router(console.router)
