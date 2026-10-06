(() => {
  const form = document.querySelector('[data-staff-register]');
  if (!form) return;
  const cards = [...form.querySelectorAll('[data-staff-member]')];
  const countLabels = document.querySelectorAll('[data-staff-count]');
  const saveButtons = document.querySelectorAll('[data-staff-save]');
  const conflict = form.dataset.staffConflict === 'true';
  const total = cards.length;
  function update() {
    const counts = {Present: 0, Absent: 0, Leave: 0, Holiday: 0, Unrecorded: 0};
    for (const card of cards) {
      const status = card.querySelector('input[type="radio"]:checked')?.value || 'Unrecorded';
      counts[status] += 1;
      card.querySelectorAll('[data-staff-time]').forEach(input => { input.disabled = status !== 'Present'; });
    }
    countLabels.forEach(label => { label.textContent = counts[label.dataset.staffCount]; });
    form.querySelector('[data-staff-progress]').textContent = `${total - counts.Unrecorded} of ${total} staff marked`;
    saveButtons.forEach(button => { button.disabled = conflict || counts.Unrecorded === total; });
  }
  form.addEventListener('change', update);
  form.addEventListener('submit', () => {
    saveButtons.forEach(button => { button.disabled = true; });
    form.querySelector('[data-staff-save-hint]').textContent = 'Saving attendance…';
  });
  update();
})();
