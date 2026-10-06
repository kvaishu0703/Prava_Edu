(() => {
  const bar = document.querySelector('[data-portal-live]');
  if (!bar) return;
  const status = bar.querySelector('[data-live-status]');
  const clock = bar.querySelector('[data-college-clock]');
  const refresh = bar.querySelector('[data-refresh-portal]');
  const original = Number(bar.dataset.revision);
  const auto = bar.dataset.autoRefresh === 'true';
  const scrollKey = `prava-scroll:${location.pathname}${location.search}`;
  let dirty = false, busy = false;
  const clockFormat = new Intl.DateTimeFormat('en-IN', {timeZone:'Asia/Kolkata', weekday:'short', day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit', second:'2-digit'});
  const showClock = () => { clock.textContent = `${clockFormat.format(new Date())} IST`; };
  const reload = () => {
    sessionStorage.setItem(scrollKey, String(window.scrollY));
    location.reload();
  };
  const savedScroll = sessionStorage.getItem(scrollKey);
  if (savedScroll !== null) {
    sessionStorage.removeItem(scrollKey);
    requestAnimationFrame(() => window.scrollTo(0, Number(savedScroll)));
  }
  const markDirty = event => {
    if (!event.target.matches('input,select,textarea,[contenteditable="true"]')) return;
    dirty = true;
    refresh.hidden = true;
    if (bar.dataset.connection === 'updates') status.textContent = 'Updates available · save your changes first';
  };
  document.addEventListener('input', markDirty);
  document.addEventListener('change', markDirty);
  refresh.addEventListener('click', () => { if (!dirty) reload(); });
  showClock();
  setInterval(showClock, 1000);
  async function check() {
    if (busy || document.hidden) return;
    busy = true;
    try {
      const response = await fetch(bar.dataset.stateUrl, {cache:'no-store', credentials:'same-origin', headers:{'Accept':'application/json'}});
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error('Session unavailable');
      const data = await response.json();
      if (data.version !== original) {
        const editing = document.activeElement?.matches('input,select,textarea,[contenteditable="true"]');
        if (auto && !dirty && !editing) { reload(); return; }
        status.textContent = dirty ? 'Updates available · save your changes first' : 'Updates available';
        refresh.hidden = dirty;
        bar.dataset.connection = 'updates';
      } else {
        status.textContent = 'Connected · checks every 15 seconds';
        bar.dataset.connection = 'online';
      }
    } catch (_) {
      status.textContent = 'Connection paused · retrying';
      bar.dataset.connection = 'paused';
    } finally { busy = false; }
  }
  setInterval(check, 15000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) check(); });
})();
