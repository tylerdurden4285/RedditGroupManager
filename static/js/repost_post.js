window.addEventListener('DOMContentLoaded', () => {
  document.addEventListener('submit', evt => {
    const form = evt.target.closest('.repost-post-form');
    if (form) {
      const skipConfirm = form.id === 'repostSelectedForm' || form.dataset.confirm === 'false';
      if (!skipConfirm && !confirm('Repost this post?')) {
        evt.preventDefault();
        return;
      }
      const cell = form.closest('td');
      if (cell) {
        cell.innerHTML = '<span class="text-gray-500">Reposting…</span>';
        cell.dataset.reposting = 'true';
      }

      let ids = [];
      if (form.id === 'repostSelectedForm') {
        const input = document.getElementById('repost-post-ids');
        if (input && input.value) {
          ids = input.value.split(',').filter(id => id);
        }
      } else {
        const match = form.action.match(/\/posts\/(\d+)\/repost/);
        if (match) {
          ids = [match[1]];
        }
      }
      ids.forEach(id => addRepostingId(parseInt(id, 10)));
    }
  });
});
