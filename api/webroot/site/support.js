const form = document.querySelector('[data-support-form]');
const status = document.querySelector('[data-form-status]');

if (form && status) {
  if (new URLSearchParams(window.location.search).get('gesendet') === '1') {
    status.textContent = 'Danke! Deine Anfrage wurde gesendet.';
    status.className = 'form-status success';
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;

    const button = form.querySelector('button[type="submit"]');
    const data = Object.fromEntries(new FormData(form).entries());
    button.disabled = true;
    status.textContent = 'Anfrage wird gesendet …';
    status.className = 'form-status';

    try {
      const response = await fetch(form.action, {
        method: 'POST',
        headers: {'Accept': 'application/json', 'Content-Type': 'application/json'},
        credentials: 'omit',
        body: JSON.stringify(data),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || 'Die Anfrage konnte nicht gesendet werden.');
      form.reset();
      status.textContent = 'Danke! Deine Anfrage wurde gesendet.';
      status.className = 'form-status success';
    } catch (error) {
      status.textContent = error instanceof Error ? error.message : 'Die Anfrage konnte nicht gesendet werden.';
      status.className = 'form-status error';
    } finally {
      button.disabled = false;
    }
  });
}
