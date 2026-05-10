"""
Inference engine.

Loads the Generator and Decoder weights ONCE at startup and exposes
two pure functions: hide(cover, secret) and reveal(stego).

The math (residual formula, normalization, clamping) is bit-for-bit identical
to the training/notebook code so PSNR results match.
"""
import io
import math
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms

from app.config import (
    G_WEIGHTS_PATH,
    DEC_WEIGHTS_PATH,
    D_WEIGHTS_PATH,
    IMG_SIZE,
    RESIDUAL_SCALE,
    MIN_RESIDUAL,
)
from app.models.architecture import Generator, DeepUNetDecoder


class StegoEngine:
    """Singleton-ish wrapper around the two networks."""

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.G: Generator | None = None
        self.Dec: DeepUNetDecoder | None = None
        self._loaded = False

        # Same preprocessing as the notebook (CELL 4)
        self.preprocess = transforms.Compose(
            [
                transforms.Resize(int(IMG_SIZE * 1.12)),
                transforms.CenterCrop(IMG_SIZE),
                transforms.ToTensor(),
                transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
            ]
        )

    # ──────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────
    def load(self):
        """Load weights into memory. Call once at app startup."""
        if self._loaded:
            return

        if not G_WEIGHTS_PATH.exists():
            raise FileNotFoundError(f"Generator weights not found: {G_WEIGHTS_PATH}")
        if not DEC_WEIGHTS_PATH.exists():
            raise FileNotFoundError(f"Decoder weights not found: {DEC_WEIGHTS_PATH}")

        self.G = Generator().to(self.device)
        self.Dec = DeepUNetDecoder(in_channels=3, base=32).to(self.device)

        self.G.load_state_dict(
            torch.load(G_WEIGHTS_PATH, map_location=self.device)
        )
        self.Dec.load_state_dict(
            torch.load(DEC_WEIGHTS_PATH, map_location=self.device)
        )

        self.G.eval()
        self.Dec.eval()

        # Discriminator is not used at inference time, but we silently note its presence.
        self.has_discriminator = D_WEIGHTS_PATH.exists()

        self._loaded = True

    def assert_loaded(self):
        if not self._loaded:
            raise RuntimeError("Models not loaded. Call engine.load() at startup.")

    # ──────────────────────────────────────────────────────────────
    # Tensor <-> bytes helpers
    # ──────────────────────────────────────────────────────────────
    def bytes_to_tensor(self, raw: bytes) -> torch.Tensor:
        """Decode an uploaded image into a (1,3,128,128) tensor in [-1,1]."""
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        return self.preprocess(img).unsqueeze(0).to(self.device)

    @staticmethod
    def tensor_to_png_bytes(t: torch.Tensor) -> bytes:
        """(1,3,H,W) or (3,H,W) tensor in [-1,1] → PNG bytes (lossless)."""
        t = t.detach().cpu()
        if t.dim() == 4:
            t = t.squeeze(0)
        t = ((t + 1) / 2).clamp(0, 1)
        arr = (t.permute(1, 2, 0).numpy() * 255).round().astype("uint8")
        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    @staticmethod
    def tensor_to_jpeg_bytes(t: torch.Tensor, quality: int = 95) -> bytes:
        """(1,3,H,W) or (3,H,W) tensor in [-1,1] → JPEG bytes."""
        t = t.detach().cpu()
        if t.dim() == 4:
            t = t.squeeze(0)
        t = ((t + 1) / 2).clamp(0, 1)
        arr = (t.permute(1, 2, 0).numpy() * 255).round().astype("uint8")
        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

    # ──────────────────────────────────────────────────────────────
    # Core ops
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _apply_residual(cover: torch.Tensor, gen_out: torch.Tensor) -> torch.Tensor:
        """Exact residual formula from training (CELL 4: apply_residual)."""
        residual = gen_out * RESIDUAL_SCALE
        res_norm = residual.abs().mean(dim=[1, 2, 3], keepdim=True).clamp(min=1e-8)
        residual = residual * torch.clamp(res_norm / MIN_RESIDUAL, max=1.0).float()
        return torch.clamp(cover + residual, -1.0, 1.0)

    @staticmethod
    def _psnr(a: torch.Tensor, b: torch.Tensor, data_range: float = 2.0) -> float:
        mse = F.mse_loss(a.float(), b.float()).item()
        if mse == 0:
            return float("inf")
        return 10 * math.log10(data_range ** 2 / mse)

    @torch.no_grad()
    def hide(self, cover_bytes: bytes, secret_bytes: bytes) -> dict:
        """
        Hide `secret` inside `cover`. Returns a dict with stego/recovered tensors
        and PSNR metrics. The caller decides which to encode/return.
        """
        self.assert_loaded()
        cover = self.bytes_to_tensor(cover_bytes)
        secret = self.bytes_to_tensor(secret_bytes)

        gen_out = self.G(cover, secret)
        stego = self._apply_residual(cover, gen_out)
        recovered = self.Dec(stego)

        return {
            "cover": cover,
            "secret": secret,
            "stego": stego,
            "recovered": recovered,
            "stego_psnr": self._psnr(stego, cover),
            "recovery_psnr": self._psnr(recovered, secret),
        }

    @torch.no_grad()
    def reveal(self, stego_bytes: bytes) -> dict:
        """Recover the hidden secret from a stego image."""
        self.assert_loaded()
        stego = self.bytes_to_tensor(stego_bytes)
        recovered = self.Dec(stego)
        return {"stego": stego, "recovered": recovered}


# Module-level singleton — imported by routers
engine = StegoEngine()
