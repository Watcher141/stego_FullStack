// ─────────────────────────────────────────
// VEIL — Reveal flow
// User uploads stego image → backend decodes → returns recovered secret.
// ─────────────────────────────────────────

function initRevealPanel() {
  setupDrop($('#drop-stego'), $('#file-stego'), $('#preview-stego'), (f) => {
    state.stego = f;
    $('#btn-reveal').disabled = false;
  });

  setupSegment('fmt-reveal', (fmt) => state.fmtReveal = fmt);

  const btn = $('#btn-reveal');
  btn.setAttribute('type', 'button');
  btn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    runReveal();
  });
}

async function runReveal() {
  if (!state.stego) return;

  setLoading('btn-reveal', 'btn-reveal-label', true);
  $('#results-reveal').classList.remove('show');
  const t0 = performance.now();

  const fd = new FormData();
  fd.append('stego', state.stego);

  try {
    const r = await fetch(`${API_URL}/api/reveal?fmt=${state.fmtReveal}`, {
      method: 'POST',
      body: fd,
    });

    if (!r.ok) {
      let errMsg = `HTTP ${r.status}`;
      try {
        const errJson = await r.json();
        errMsg = errJson.detail || errMsg;
      } catch {
        errMsg = (await r.text()) || errMsg;
      }
      throw new Error(errMsg);
    }

    const blob = await r.blob();
    const blobUrl = URL.createObjectURL(blob);

    const img = $('#img-recovered');
    img.onload = () => {
      $('#reveal-time').textContent = `${((performance.now() - t0) / 1000).toFixed(2)}s ⁄ ${(blob.size / 1024).toFixed(1)} kB`;
      $('#results-reveal').classList.add('show');
      setLoading('btn-reveal', 'btn-reveal-label', false, 'Decode');
    };
    img.onerror = () => {
      showAlert('Failed to render recovered image — backend returned data but the browser could not decode it.');
      setLoading('btn-reveal', 'btn-reveal-label', false, 'Decode');
    };
    img.src = blobUrl;

    $('#dl-recovered').onclick   = (e) => { e.preventDefault(); downloadUrl(blobUrl, `recovered.${state.fmtReveal}`); };
    $('#open-recovered').onclick = (e) => { e.preventDefault(); openUrl(blobUrl); };
  } catch (err) {
    console.error(err);
    showAlert(`Decoding failed: ${err.message}`);
    setLoading('btn-reveal', 'btn-reveal-label', false, 'Decode');
  }
}