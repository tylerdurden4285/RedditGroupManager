window.addEventListener('DOMContentLoaded', () => {
  document.addEventListener('submit', evt => {
    const form = evt.target.closest('.undo-post-form');
    if (form) {
      const skipConfirm =
        form.id === 'undoSelectedForm' || form.dataset.confirm === 'false';
      if (!skipConfirm && !confirm('Remove this post from Reddit?')) {
        evt.preventDefault();
        return;
      }

      const cell = form.closest('td');
      if (cell) {
        cell.innerHTML = '<span class="text-gray-500">Undoing…</span>';
        cell.dataset.undoing = 'true';
      }

      // store ids being undone so we can restore state after redirect
      let ids = [];
      if (form.id === 'undoSelectedForm') {
        const input = document.getElementById('undo-post-ids');
        if (input && input.value) {
          ids = input.value.split(',').filter(id => id);
        }
      } else {
        const match = form.action.match(/\/posts\/(\d+)\/undo/);
        if (match) {
          ids = [match[1]];
        }
      }
      ids.forEach(id => addUndoingId(parseInt(id, 10)));
    }
  });
});
