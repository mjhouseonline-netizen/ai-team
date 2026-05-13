(function () {
    function hideGuide(el) {
        if (el) el.style.display = 'none';
    }

    function initGuide(el) {
        const key = el.getAttribute('data-guide-key');
        if (!key) return;

        const hidden = localStorage.getItem(`guide.hide.${key}`) === '1';
        const dismissed = sessionStorage.getItem(`guide.dismiss.${key}`) === '1';
        if (hidden || dismissed) {
            hideGuide(el);
            return;
        }

        el.addEventListener('click', function (e) {
            const btn = e.target.closest('[data-guide-action]');
            if (!btn) return;
            const action = btn.getAttribute('data-guide-action');
            if (action === 'dismiss') {
                sessionStorage.setItem(`guide.dismiss.${key}`, '1');
                hideGuide(el);
            }
            if (action === 'hide') {
                localStorage.setItem(`guide.hide.${key}`, '1');
                hideGuide(el);
            }
        });
    }

    function initAll() {
        document.querySelectorAll('.onboarding-guide[data-guide-key]').forEach(initGuide);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAll);
    } else {
        initAll();
    }
})();
