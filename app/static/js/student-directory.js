(() => {
  const directory = document.querySelector('[data-student-directory]');
  if (!directory) return;
  const boxes = [...directory.querySelectorAll('[data-student-select]')];
  const all = directory.querySelector('[data-select-all]');
  const buttons = [...directory.querySelectorAll('[data-open-action]')];
  const selected = () => boxes.filter(box => box.checked);
  function updateSelection() {
    const rows = selected();
    directory.querySelector('[data-selection-count]').textContent = `${rows.length} selected`;
    all.checked = !!rows.length && rows.length === boxes.length;
    all.indeterminate = !!rows.length && rows.length !== boxes.length;
    buttons.forEach(button => {
      const archived = button.dataset.openAction === 'restore';
      button.disabled = !rows.length || rows.length > 500 || rows.some(box => (box.dataset.archived === 'true') !== archived);
    });
  }
  all.addEventListener('change', () => { boxes.forEach(box => {box.checked = all.checked;}); updateSelection(); });
  boxes.forEach(box => box.addEventListener('change', updateSelection));
  directory.querySelector('[data-select-generated]').addEventListener('click', () => {
    boxes.forEach(box => {box.checked = box.dataset.source === 'generated' && box.dataset.archived !== 'true';});
    updateSelection();
    directory.querySelector('[data-student-select]')?.dispatchEvent(new Event('input', {bubbles:true}));
  });
  const element = document.getElementById('studentActionModal');
  const form = element.querySelector('form');
  const confirmed = document.getElementById('studentActionConfirmed');
  const submit = element.querySelector('[data-confirm-submit]');
  function openConfirmation(action, rows) {
    if (!rows.length || rows.length > 500) return;
    const restore = action === 'restore';
    if (rows.some(box => (box.dataset.archived === 'true') !== restore)) return;
    form.reset();
    element.querySelector('[data-action-value]').value = action;
    element.querySelector('[data-confirm-count]').value = rows.length;
    element.querySelector('[data-confirm-title]').textContent = `${restore ? 'Restore' : 'Remove'} ${rows.length} student account(s)?`;
    element.querySelector('[data-confirm-explanation]').textContent = restore
      ? 'These students will return to class lists and can sign in using their existing login ID and password.'
      : 'These students will be removed from current class lists and cannot sign in. Their attendance, marks and submissions remain saved and can be restored.';
    const names = element.querySelector('[data-confirm-names]');
    const ids = element.querySelector('[data-confirm-ids]');
    names.replaceChildren(); ids.replaceChildren();
    rows.forEach(box => {
      const li = document.createElement('li'); li.textContent = `${box.dataset.name} · ${box.dataset.enrolment}`; names.append(li);
      const input = document.createElement('input'); input.type = 'hidden'; input.name = 'student_ids'; input.value = box.value; ids.append(input);
    });
    submit.textContent = `${restore ? 'Restore' : 'Remove'} ${rows.length} student account(s)`;
    submit.className = `btn ${restore ? 'btn-primary' : 'btn-danger'}`;
    submit.disabled = true;
    confirmed.dispatchEvent(new Event('change', {bubbles:true}));
    bootstrap.Modal.getOrCreateInstance(element).show();
  }
  confirmed.addEventListener('change', () => {submit.disabled = !confirmed.checked;});
  buttons.forEach(button => button.addEventListener('click', () => openConfirmation(button.dataset.openAction, selected())));
  directory.querySelectorAll('[data-single-action]').forEach(button => button.addEventListener('click', () => {
    openConfirmation(button.dataset.singleAction, boxes.filter(box => box.value === button.dataset.studentId));
  }));
  form.addEventListener('submit', () => {submit.disabled = true; submit.textContent = 'Saving…';});
  updateSelection();
})();
