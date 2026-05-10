"""
FastAPI entrypoint for the steganography backend.

Run locally:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import CORS_ORIGINS
from app.inference import engine
from app.routers import stego

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("stego.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Loading model weights...")
    try:
        engine.load()
        log.info(
            "Models ready on %s (discriminator present: %s)",
            engine.device,
            getattr(engine, "has_discriminator", False),
        )
    except Exception as e:
        log.exception("Failed to load weights: %s", e)
        raise
    yield
    log.info("Shutting down.")


app = FastAPI(
    title="VEIL — Steganography API",
    description="Hide one image inside another using a CSP-Generator + DeepUNet decoder.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Stego-PSNR-dB", "X-Recovery-PSNR-dB"],
)

app.include_router(stego.router)


# ─────────────────────────────────────────────────────────────────
# Mount frontend (if present)
# ─────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "veil_frontend"

if FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists():
    log.info("Serving frontend from %s", FRONTEND_DIR)
    app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

else:
    log.info("No veil_frontend/ found — serving JSON at root")

    @app.get("/", tags=["root"])
    async def root():
        return {
            "name": "VEIL Steganography API",
            "endpoints": {
                "hide":      "POST /api/hide      (multipart: cover, secret) → image bytes",
                "hide_full": "POST /api/hide/full (multipart: cover, secret) → JSON",
                "reveal":    "POST /api/reveal    (multipart: stego)          → image bytes",
                "health":    "GET  /api/health",
                "docs":      "GET  /docs",
            },
        }