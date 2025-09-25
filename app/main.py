"""
main.py
--------
FastAPI server for Semi-Automatic Dryer Computer.

Endpoints:
- GET /data   -> JSON with temps (°F), moisture (%), bushels/hr
- GET /status -> simple health check
- GET /       -> serves static/index.html (kiosk UI)
"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from app.logic import get_processed_data

# Create FastAPI app
app = FastAPI()

# Allow kiosk or other clients to fetch data
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can tighten this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === ROUTES ===

@app.get("/status")
def status():
    """Return simple health check."""
    return {"status": "ok", "message": "Dryer computer running"}


@app.get("/data")
def data():
    """Return processed dryer data."""
    return get_processed_data()


@app.get("/")
def serve_ui():
    """Serve kiosk UI page (static/index.html)."""
    static_path = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
    return FileResponse(static_path)
