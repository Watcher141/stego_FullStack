// ─────────────────────────────────────────
// VEIL — backend health check (top-right indicator)
// ─────────────────────────────────────────

async function checkHealth() {
  const status = $('#status');
  const txt = $('#statusText');
  try {
    const r = await fetch(`${API_URL}/api/health`);
    const j = await r.json();
    if (j.models_loaded) {
      status.classList.add('online');
      status.classList.remove('offline');
      txt.textContent = `online ⁄ ${j.device}`;
    } else {
      throw new Error('models not loaded');
    }
  } catch (e) {
    status.classList.add('offline');
    status.classList.remove('online');
    txt.textContent = 'backend offline';
  }
}
