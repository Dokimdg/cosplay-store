// Обробники подій замість інлайнових onchange/onsubmit (потрібно для CSP script-src 'self')
document.addEventListener('change', function (e) {
    if (e.target.matches('select[data-autosubmit]')) {
        e.target.form.submit();
    }
});
document.addEventListener('submit', function (e) {
    var msg = e.target.getAttribute('data-confirm');
    if (msg && !window.confirm(msg)) {
        e.preventDefault();
    }
});
