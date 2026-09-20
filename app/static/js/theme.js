/* Runs before styles are painted; works without storage access as well. */
(() => {
    const root = document.documentElement;
    const preference = window.matchMedia('(prefers-color-scheme: dark)');
    let saved;
    try { saved = localStorage.getItem('prava-theme'); } catch (_) {}
    let explicit = saved === 'dark' || saved === 'light';
    function apply(theme) {
        root.dataset.theme = theme;
        root.dataset.bsTheme = theme;
        root.style.colorScheme = theme;
        document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#0b1020' : '#f6f8fc');
        document.querySelectorAll('[data-theme-toggle]').forEach(button => {
            const dark = theme === 'dark';
            button.setAttribute('aria-pressed', String(dark));
            button.setAttribute('aria-label', dark ? 'Switch to day mode' : 'Switch to night mode');
            button.querySelector('[data-theme-label]').textContent = dark ? 'Night' : 'Day';
            button.querySelector('i').className = dark ? 'bi bi-moon-stars' : 'bi bi-sun';
        });
    }
    apply(explicit ? saved : preference.matches ? 'dark' : 'light');
    document.addEventListener('DOMContentLoaded', () => {
        apply(root.dataset.theme);
        document.querySelectorAll('[data-theme-toggle]').forEach(button => button.addEventListener('click', () => {
            const theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
            explicit = true;
            try { localStorage.setItem('prava-theme', theme); } catch (_) {}
            apply(theme);
        }));
    });
    preference.addEventListener('change', event => { if (!explicit) apply(event.matches ? 'dark' : 'light'); });
    window.addEventListener('storage', event => {
        if (event.key === 'prava-theme') {
            explicit = ['dark', 'light'].includes(event.newValue);
            apply(explicit ? event.newValue : preference.matches ? 'dark' : 'light');
        }
    });
})();
