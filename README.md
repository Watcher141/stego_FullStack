# Steganography FastAPI Backend

Hide one image inside another using a CSP-Generator + DeepUNet decoder.
Mirrors the inference pipeline from your `COCO_model.ipynb` exactly (same residual formula, normalization, preprocessing).

## Project layout

```
stego_backend/
├── app/
│   ├── main.py              # FastAPI entrypoint + lifespan loader
│   ├── config.py            # Paths and constants
│   ├── inference.py         # StegoEngine (loads weights once, hide/reveal)
│   ├── models/
│   │   └── architecture.py  # Generator + DeepUNetDecoder (verbatim from notebook)
│   ├── routers/
│   │   └── stego.py         # /api/hide, /api/hide/full, /api/reveal, /api/health
│   └── utils/
│       └── validation.py    # Upload size/mime checks
├── weights/                 # ← put your .pth files here
│   ├── G_best.pth
│   ├── Dec_best.pth
│   └── D_best.pth           # optional (not used at inference)
├── requirements.txt
└── README.md
```

## Setup

```bash
cd stego_backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Place your three weight files inside `weights/` (or set `WEIGHTS_DIR` env var to point elsewhere):

```
weights/G_best.pth
weights/Dec_best.pth
weights/D_best.pth   # optional, ignored by the API
```

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Visit `http://localhost:8000/docs` for the auto-generated Swagger UI.

## Endpoints

### `POST /api/hide`
Multipart form data: `cover`, `secret` (image files). Optional query `?fmt=png|jpeg` (default `png`).

Returns the **stego image** as raw image bytes. PSNR metrics are in response headers:
- `X-Stego-PSNR-dB`
- `X-Recovery-PSNR-dB`

### `POST /api/hide/full`
Same inputs as `/api/hide`. Returns JSON with base64-encoded stego + recovered preview + metrics. Convenient if your frontend wants a side-by-side display.

```json
{
  "stego_image": "data:image/png;base64,...",
  "recovered_image": "data:image/png;base64,...",
  "metrics": { "stego_psnr_db": 38.42, "recovery_psnr_db": 31.07 },
  "format": "png"
}
```

### `POST /api/reveal`
Multipart form data: `stego` (image file). Returns the **recovered secret** as image bytes.

### `GET /api/health`
Readiness probe — confirms weights are loaded.

## Frontend usage example

```js
const fd = new FormData();
fd.append("cover", coverFile);
fd.append("secret", secretFile);

// Get raw stego image
const res = await fetch("http://localhost:8000/api/hide?fmt=png", {
  method: "POST",
  body: fd,
});
const blob = await res.blob();
const url = URL.createObjectURL(blob);
document.querySelector("img#stego").src = url;
console.log("Stego PSNR:", res.headers.get("X-Stego-PSNR-dB"));
```

For the JSON variant:
```js
const res = await fetch("http://localhost:8000/api/hide/full", { method: "POST", body: fd });
const data = await res.json();
document.querySelector("img#stego").src = data.stego_image;
document.querySelector("img#recovered").src = data.recovered_image;
```

## Notes & gotchas

- **PNG is strongly recommended.** JPEG is lossy and will damage the hidden residual, lowering recovery PSNR. Only use `fmt=jpeg` for previews.
- **Images are resized to 128×128** to match the trained model. The output stego is also 128×128.
- **GPU** is detected automatically. On a CPU, single-image inference is still well under a second.
- **Weights are loaded once** at startup via FastAPI's lifespan; requests share the same model instance.
- **CORS** is open by default (`*`). Lock it down via `CORS_ORIGINS=https://yourdomain.com` env var in production.
- **Concurrency:** PyTorch eval is thread-safe for inference but use a single uvicorn worker if running on GPU to avoid VRAM duplication. For CPU, multiple workers are fine.

## Production hints

```bash
# Single GPU worker
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1

# CPU, multiple workers (set OMP threads low to avoid contention)
OMP_NUM_THREADS=2 uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Put it behind nginx/Caddy with TLS, and you're set.