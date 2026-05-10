// ─────────────────────────────────────────
// VEIL — shared utilities
// ─────────────────────────────────────────

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function showAlert(msg, kind = 'error') {
  const area = $('#alert-area');
  area.innerHTML = `<div class="alert ${kind}"><span class="icon">${kind === 'error' ? '✕' : 'ⓘ'}</span><span>${msg}</span></div>`;
  area.scrollIntoView({ behavior: 'smooth', block: 'center' });
  setTimeout(() => area.innerHTML = '', 7000);
}

function setupDrop(dropEl, inputEl, previewEl, onFile) {
  const update = (file) => {
    if (!file || !file.type.startsWith('image/')) return;
    const url = URL.createObjectURL(file);
    previewEl.style.backgroundImage = `url("${url}")`;
    dropEl.classList.add('has-image');
    onFile(file);
  };
  inputEl.addEventListener('change', (e) => update(e.target.files[0]));
  dropEl.addEventListener('dragover', (e) => { e.preventDefault(); dropEl.classList.add('dragover'); });
  dropEl.addEventListener('dragleave', () => dropEl.classList.remove('dragover'));
  dropEl.addEventListener('drop', (e) => {
    e.preventDefault();
    dropEl.classList.remove('dragover');
    update(e.dataTransfer.files[0]);
  });
}

function setupSegment(groupId, onSelect) {
  const buttons = $$(`#${groupId} button`);
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      onSelect(btn.dataset.fmt);
    });
  });
}

function setLoading(btnId, labelId, loading, defaultLabel) {
  const btn = $(`#${btnId}`);
  const label = $(`#${labelId}`);
  btn.disabled = loading;
  if (loading) {
    label.innerHTML = '<span class="loader"><span></span><span></span><span></span></span>';
  } else {
    label.textContent = defaultLabel;
  }
}

function downloadUrl(url, filename) {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function openUrl(url) {
  const w = window.open();
  if (w) {
    w.document.write(`<title>Image</title><body style="margin:0;background:#000;display:flex;align-items:center;justify-content:center;min-height:100vh"><img src="${url}" style="max-width:100%;max-height:100vh;image-rendering:pixelated"></body>`);
  }
}

function dataUrlSize(url) {
  const b64 = url.split(',')[1] || '';
  const bytes = Math.floor(b64.length * 3 / 4);
  return bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} kB`;
}

// ── Copy text to clipboard with visual feedback on the triggering button ──
async function copyToClipboard(text, btn) {
  try {
    await navigator.clipboard.writeText(text);
    if (btn) {
      const orig = btn.textContent;
      btn.textContent = 'copied!';
      btn.classList.add('copied');
      setTimeout(() => {
        btn.textContent = orig;
        btn.classList.remove('copied');
      }, 1500);
    }
  } catch (e) {
    showAlert('Copy failed — please select & copy manually.');
  }
}

// ── Wire up all .copy-btn buttons (data-copy="elementId") ──
function wireCopyButtons(scope = document) {
  scope.querySelectorAll('.copy-btn').forEach(btn => {
    btn.onclick = () => {
      const target = document.getElementById(btn.dataset.copy);
      if (target) copyToClipboard(target.textContent, btn);
    };
  });
}

// ── Extract stego_<id>.{png|jpg|jpeg} from a filename ──
function parseStegoId(filename) {
  if (!filename) return null;
  const m = filename.match(/^stego_([A-Za-z0-9]{4,32})\.(png|jpe?g)$/i);
  return m ? m[1] : null;
}
