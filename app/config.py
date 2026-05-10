"""
Configuration. Tweak paths here.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
# Where your three .pth files live. Override with env var WEIGHTS_DIR if you want.
WEIGHTS_DIR = Path(os.getenv("WEIGHTS_DIR", BASE_DIR / "weights"))

# Filenames — must match what you upload
G_WEIGHTS_PATH = WEIGHTS_DIR / "G_best.pth"
DEC_WEIGHTS_PATH = WEIGHTS_DIR / "Dec_best.pth"
D_WEIGHTS_PATH = WEIGHTS_DIR / "D_best.pth"  # Discriminator — not used at inference, but loaded if present

# Model / inference constants — must match training EXACTLY
IMG_SIZE = 128
RESIDUAL_SCALE = 0.05
MIN_RESIDUAL = 0.01

# API
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB per image
ALLOWED_MIME = {"image/jpeg", "image/png", "image/jpg", "image/webp"}

# CORS — set to your frontend origin in production
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
