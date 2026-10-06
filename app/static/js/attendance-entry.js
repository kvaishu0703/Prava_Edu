(() => {
  const register = document.querySelector('[data-attendance-entry]');
  if (!register) return;
  const students = [...register.querySelectorAll('[data-attendance-student]')];
  const editing = register.dataset.editing === 'true';
  const conflict = register.dataset.conflict === 'true';
  const search = register.querySelector('[data-attendance-search]');
  const saves = register.querySelectorAll('[data-attendance-save]');
  const note = register.querySelector('[data-attendance-save-note]');
  function updateCounts() {
    const counts = {Present: 0, Absent: 0, Late: 0, Unmarked: 0};
    students.forEach(row => {
      const status = editing ? row.querySelector('input[type="radio"]:checked')?.value : row.dataset.savedStatus;
      counts[Object.hasOwn(counts, status) ? status : 'Unmarked'] += 1;
    });
    register.querySelectorAll('[data-attendance-count]').forEach(item => {
      item.textContent = counts[item.dataset.attendanceCount];
    });
    saves.forEach(save => { save.disabled = conflict || counts.Unmarked > 0; });
    if (note) note.textContent = counts.Unmarked ? `${counts.Unmarked} unmarked · choose a status for every student` : `${students.length} students ready to save`;
  }
  register.addEventListener('change', event => {
    if (event.target.matches('input[type="radio"]')) updateCounts();
  });
  register.querySelector('[data-all-present]')?.addEventListener('click', () => {
    students.forEach(row => {
      const present = row.querySelector('input[type="radio"][value="Present"]');
      if (present) {
        present.checked = true;
        present.dispatchEvent(new Event('change', {bubbles: true}));
      }
    });
    updateCounts();
  });
  search?.addEventListener('input', () => {
    const query = search.value.trim().toLocaleLowerCase();
    let visible = 0;
    students.forEach(row => {
      row.hidden = !row.dataset.search.includes(query);
      if (!row.hidden) visible += 1;
    });
    register.querySelector('[data-visible-count]').textContent = `${visible} of ${students.length} students shown`;
    register.querySelector('[data-attendance-no-results]').hidden = visible !== 0;
  });
  updateCounts();
})();
