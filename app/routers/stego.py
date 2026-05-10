"""
Routes:
  POST /api/hide       — multipart: cover, secret  → stego image (raw bytes)
  POST /api/hide/full  — multipart: cover, secret  → JSON with stego/recovered + metrics
  POST /api/reveal     — multipart: stego          → recovered secret image
  GET  /api/health     — liveness probe
"""
import base64

from fastapi import APIRouter, File, UploadFile, Query, HTTPException
from fastapi.responses import Response, JSONResponse

from app.inference import engine
from app.utils.validation import read_image_upload

router = APIRouter(prefix="/api", tags=["stego"])


def _encode_tensor(tensor, fmt: str) -> bytes:
    if fmt == "jpeg":
        return engine.tensor_to_jpeg_bytes(tensor)
    return engine.tensor_to_png_bytes(tensor)


def _media_type(fmt: str) -> str:
    return "image/jpeg" if fmt == "jpeg" else "image/png"


# ─────────────────────────────────────────────────────────────────
# /api/hide  — returns the stego image as raw bytes
# ─────────────────────────────────────────────────────────────────
@router.post(
    "/hide",
    responses={200: {"content": {"image/png": {}, "image/jpeg": {}}}},
    summary="Hide a secret image inside a cover image (raw bytes response)",
)
async def hide(
    cover: UploadFile = File(..., description="Cover image (the visible one)"),
    secret: UploadFile = File(..., description="Secret image (to be hidden)"),
    fmt: str = Query("png", pattern="^(png|jpeg)$", description="Output format"),
):
    cover_bytes = await read_image_upload(cover, "cover")
    secret_bytes = await read_image_upload(secret, "secret")

    try:
        result = engine.hide(cover_bytes, secret_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}")

    img_bytes = _encode_tensor(result["stego"], fmt)
    return Response(
        content=img_bytes,
        media_type=_media_type(fmt),
        headers={
            "X-Stego-PSNR-dB": f"{result['stego_psnr']:.3f}",
            "X-Recovery-PSNR-dB": f"{result['recovery_psnr']:.3f}",
            "Content-Disposition": f'inline; filename="stego.{fmt}"',
        },
    )


# ─────────────────────────────────────────────────────────────────
# /api/hide/full  — JSON with base64 stego + recovered + metrics
# ─────────────────────────────────────────────────────────────────
@router.post(
    "/hide/full",
    summary="Hide and return base64 stego + recovered preview + PSNR metrics",
)
async def hide_full(
    cover: UploadFile = File(...),
    secret: UploadFile = File(...),
    fmt: str = Query("png", pattern="^(png|jpeg)$"),
):
    cover_bytes = await read_image_upload(cover, "cover")
    secret_bytes = await read_image_upload(secret, "secret")

    try:
        result = engine.hide(cover_bytes, secret_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}")

    stego_b = _encode_tensor(result["stego"], fmt)
    recov_b = _encode_tensor(result["recovered"], fmt)
    mime = _media_type(fmt)

    return JSONResponse(
        {
            "stego_image": f"data:{mime};base64,{base64.b64encode(stego_b).decode()}",
            "recovered_image": f"data:{mime};base64,{base64.b64encode(recov_b).decode()}",
            "metrics": {
                "stego_psnr_db": round(result["stego_psnr"], 3),
                "recovery_psnr_db": round(result["recovery_psnr"], 3),
            },
            "format": fmt,
        }
    )


# ─────────────────────────────────────────────────────────────────
# /api/reveal  — recover secret from a stego image
# ─────────────────────────────────────────────────────────────────
@router.post(
    "/reveal",
    responses={200: {"content": {"image/png": {}, "image/jpeg": {}}}},
    summary="Recover the hidden secret from a stego image",
)
async def reveal(
    stego: UploadFile = File(..., description="Stego image to decode"),
    fmt: str = Query("png", pattern="^(png|jpeg)$"),
):
    stego_bytes = await read_image_upload(stego, "stego")

    try:
        result = engine.reveal(stego_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}")

    img_bytes = _encode_tensor(result["recovered"], fmt)
    return Response(
        content=img_bytes,
        media_type=_media_type(fmt),
        headers={"Content-Disposition": f'inline; filename="recovered.{fmt}"'},
    )


# ─────────────────────────────────────────────────────────────────
# /api/health
# ─────────────────────────────────────────────────────────────────
@router.get("/health", summary="Liveness / readiness check")
async def health():
    return {
        "status": "ok",
        "models_loaded": engine._loaded,
        "device": str(engine.device),
        "discriminator_present": getattr(engine, "has_discriminator", False),
    }