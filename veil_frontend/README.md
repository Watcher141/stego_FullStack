- **Per-stego password protection.** Every stego image is locked with a password (auto-generated or user-chosen). Only someone with the password can decode it on this server.
- **SQLite database** (`veil.db` auto-created) stores `stego_id → bcrypt(password_hash)`. Passwords themselves are never stored.
- **Stego ID embedded in filename** (e.g. `stego_xR7Kp9.png`) — the reveal endpoint reads it automatically.
- **New password UI** — generate button, show/hide toggle, copy buttons, prominent credential display.

## Files changed vs v1

| File | Status | Notes |
|------|--------|-------|
| `app/storage.py` | **NEW** | SQLite + bcrypt module |
| `app/routers/stego.py` | UPDATED | Password handling, dropped plain `/api/hide` endpoint |
| `app/main.py` | UPDATED | Initializes DB at startup |
| `requirements.txt` | UPDATED | Added `bcrypt>=4.1.0` |
| `veil_frontend/*` | UPDATED | Password input, credential card, filename validation |

## Files unchanged

- `app/config.py`
- `app/inference.py`
- `app/models/architecture.py`
- `app/utils/validation.py`

## Upgrade from v1

1. Replace your existing `stego_backend/` files with these (keep your `weights/` folder and `.venv/` as-is)
2. Install bcrypt:
   ```bash
   pip install bcrypt
   ```
3. Restart uvicorn:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Visit `http://127.0.0.1:8000/`

A new file `veil.db` will appear in your project root — that's your password database.

## API changes

### `POST /api/hide/full`

**New:** accepts optional `password` form field.

```bash
# With auto-generated password
curl -F "cover=@cover.jpg" -F "secret=@secret.jpg" \
     http://127.0.0.1:8000/api/hide/full

# With user-chosen password
curl -F "cover=@cover.jpg" -F "secret=@secret.jpg" -F "password=mySecret123" \
     http://127.0.0.1:8000/api/hide/full
```

**Response (new fields):**
```json
{
  "stego_id": "xR7Kp9Mn",
  "filename": "stego_xR7Kp9Mn.png",
  "password": "kp7-mn3-vQ4x",
  "password_generated": true,
  "stego_image": "data:image/png;base64,...",
  "recovered_image": "data:image/png;base64,...",
  "metrics": { "stego_psnr_db": 38.42, "recovery_psnr_db": 28.91 },
  "format": "png"
}
```

### `POST /api/reveal`

**New:** requires `password` form field. Filename must match `stego_<id>.<ext>` pattern.

```bash
curl -F "stego=@stego_xR7Kp9Mn.png" -F "password=kp7-mn3-vQ4x" \
     -o recovered.png http://127.0.0.1:8000/api/reveal
```

**Errors:**
- `400` — filename not in `stego_<id>.<ext>` format
- `401` — wrong password or unknown stego_id (same error to avoid leaking which)

### Removed: `POST /api/hide`

The unprotected raw-bytes hide endpoint is gone — everything goes through `/api/hide/full` now.

## Security notes

- **Passwords hashed with bcrypt** (12 rounds). Plaintext passwords never stored.
- **Server-side enforcement only** — if someone steals your weights AND your stego.png, they can decode it on their own server. The lock is only effective on this deployment. (For true cryptographic privacy, you'd encrypt the secret pixels client-side before hiding — that's a different feature.)
- **No rate limiting** out of the box. For production, add slowapi or nginx rate limits to prevent password brute-forcing.
- `veil.db` should be backed up if you need to preserve recovery ability for old stegos.

## Reset the database

To wipe all stored stego records (orphaning all old stego files):
```bash
rm veil.db
```
The DB is recreated empty on next startup.