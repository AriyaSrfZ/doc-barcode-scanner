"""
Run locally with: uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import qr

Base.metadata.create_all(bind=engine)

app = FastAPI(title="QR Generator Service", version="0.1.0")


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.include_router(qr.router)
