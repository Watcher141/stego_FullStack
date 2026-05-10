// ─────────────────────────────────────────
// VEIL — App entry point
// ─────────────────────────────────────────

$$('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    $$('.tab').forEach(t => t.classList.remove('active'));
    $$('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    $(`#panel-${tab.dataset.panel}`).classList.add('active');
  });
});

initHidePanel();
initRevealPanel();

checkHealth();
setInterval(checkHealth, 15000);
