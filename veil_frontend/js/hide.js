// ─────────────────────────────────────────
// VEIL — Hide flow
// User uploads cover + secret, gets stego + recovered preview.
// ─────────────────────────────────────────

function initHidePanel() {
  setupDrop($('#drop-cover'), $('#file-cover'), $('#preview-cover'), (f) => {
    state.cover = f;
    updateHideButton();
  });

  setupDrop($('#drop-secret'), $('#file-secret'), $('#preview-secret'), (f) => {
    state.secret = f;
    updateHideButton();
  });

  setupSegment('fmt-hide', (fmt) => state.fmtHide = fmt);

  const btn = $('#btn-hide');
  btn.setAttribute('type', 'button');
  btn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    runHide();
  });
}

function updateHideButton() {
  $('#btn-hide').disabled = !(state.cover && state.secret);
}

// ── Convert "data:image/png;base64,..." → Blob URL (reliable for downloads of any size) ──
function dataUrlToBlobUrl(dataUrl) {
  const match = dataUrl.match(/^data:([^;]+);base64,(.+)$/);
  if (!match) return dataUrl;
  const mime = match[1];
  const b64 = match[2];
  const binaryStr = atob(b64);
  const bytes = new Uint8Array(binaryStr.length);
  for (let i = 0; i < binaryStr.length; i++) bytes[i] = binaryStr.charCodeAt(i);
  const blob = new Blob([bytes], { type: mime });
  return URL.createObjectURL(blob);
}

async function runHide() {
  if (!state.cover || !state.secret) return;

  setLoading('btn-hide', 'btn-hide-label', true);
  $('#results-hide').classList.remove('show');
  const t0 = performance.now();

  const fd = new FormData();
  fd.append('cover', state.cover);
  fd.append('secret', state.secret);

  try {
    const r = await fetch(`${API_URL}/api/hide/full?fmt=${state.fmtHide}`, {
      method: 'POST',
      body: fd,
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }));
      throw new Error(err.detail || `HTTP ${r.status}`);
    }
    const data = await r.json();

    const stegoBlobUrl = dataUrlToBlobUrl(data.stego_image);
    const recBlobUrl   = dataUrlToBlobUrl(data.recovered_image);

    $('#img-stego').src = stegoBlobUrl;
    $('#img-rec').src   = recBlobUrl;
    $('#m-stego').textContent = data.metrics.stego_psnr_db.toFixed(2);
    $('#m-rec').textContent   = data.metrics.recovery_psnr_db.toFixed(2);
    $('#stego-size').textContent = `${data.format.toUpperCase()} ⁄ ~${dataUrlSize(data.stego_image)}`;
    $('#hide-time').textContent  = `${((performance.now() - t0) / 1000).toFixed(2)}s`;

    $('#dl-stego').onclick   = (e) => { e.preventDefault(); downloadUrl(stegoBlobUrl, `stego.${data.format}`); };
    $('#dl-rec').onclick     = (e) => { e.preventDefault(); downloadUrl(recBlobUrl, `recovered_preview.${data.format}`); };
    $('#open-stego').onclick = (e) => { e.preventDefault(); openUrl(stegoBlobUrl); };
    $('#open-rec').onclick   = (e) => { e.preventDefault(); openUrl(recBlobUrl); };

    $('#results-hide').classList.add('show');
  } catch (err) {
    console.error(err);
    showAlert(`Encoding failed: ${err.message}`);
  } finally {
    setLoading('btn-hide', 'btn-hide-label', false, 'Encode');
  }
}