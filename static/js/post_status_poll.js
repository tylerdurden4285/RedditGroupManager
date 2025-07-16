function getStatusClasses(status) {
  switch (status) {
    case 'posted':
      return 'bg-green-100 text-green-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    case 'overdue':
      return 'bg-red-100 text-red-800';
    case 'retrying':
      return 'bg-yellow-100 text-yellow-800';
    case 'processing':
      return 'bg-blue-100 text-blue-800';
    case 'waiting':
      return 'bg-purple-100 text-purple-800';
    case 'awaiting':
      return 'bg-yellow-100 text-yellow-800';
    case 'filtered':
      return 'bg-red-100 text-red-800';
    case 'scheduled':
      return 'bg-orange-100 text-orange-800';
    case 'undone':
      return 'bg-gray-300 text-gray-800';
    case 'deleted':
      return 'bg-gray-300 text-gray-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

async function pollStatuses() {
  const idInputs = document.querySelectorAll('.post-select-checkbox');
  const ids = Array.from(idInputs).map(el => el.value).filter(Boolean);
  const query = ids.length ? `?ids=${ids.join(',')}` : '';
  const resp = await fetch(`/posts/statuses${query}`);
  if (!resp.ok) {
    return;
  }
  const data = await resp.json();
  let allFinal = true;
  data.forEach(p => {
    const span = document.getElementById('status-span-' + p.id);
    const urlCell = document.getElementById('reddit-url-cell-' + p.id);
    const undoing = urlCell && urlCell.dataset.undoing === 'true';
    const reposting = urlCell && urlCell.dataset.reposting === 'true';
    const detailsBtn = document.getElementById('details-btn-' + p.id);
    if (span) {
      let display = p.status || 'n/a';
      if (p.status === 'retrying') {
        display = `retry ${p.retry_count}/${window.max_retries}`;
      }
      span.textContent = display;
      span.className = 'px-2 py-1 rounded-full text-xs font-medium ' + getStatusClasses(p.status);
      span.title = p.error_message || '';
    }
    if (urlCell) {
      if (reposting) {
        if (p.status === 'processing' || p.status === 'waiting') {
          // keep "Reposting…" text until status changes
        } else {
          delete urlCell.dataset.reposting;
          removeRepostingId(p.id);
        }
      }
      if (p.status === 'posted' && p.reddit_url) {
        if (urlCell.dataset.undoing === 'true') {
          // keep "Undoing…" text until status changes
        } else {
          urlCell.innerHTML = `<a href="${p.reddit_url}" target="_blank" class="inline-flex items-center px-3 py-1 bg-indigo-500 text-white whitespace-nowrap rounded-full border border-indigo-500 hover:bg-indigo-600">See on Reddit</a>`;
        }
      } else if (p.status === 'failed' || p.status === 'overdue') {
        delete urlCell.dataset.undoing;
        removeUndoingId(p.id);
        const html = `<div class="flex items-center space-x-2"><form method="post" action="/posts/${p.id}/repost"><button class="text-blue-600">Repost</button></form></div>`;
        urlCell.innerHTML = html;
      } else if (p.status === 'awaiting') {
        if (p.reddit_url) {
          urlCell.innerHTML = `<a href="${p.reddit_url}" target="_blank" class="text-gray-500 underline">Awaiting Moderation</a>`;
        } else {
          urlCell.innerHTML = '<span class="text-gray-500">Awaiting Moderation</span>';
        }
      } else if (p.status === 'filtered') {
        if (p.reddit_url) {
          urlCell.innerHTML = `<a href="${p.reddit_url}" target="_blank" class="text-gray-500 underline">Filtered by Reddit</a>`;
        } else {
          urlCell.innerHTML = '<span class="text-gray-500">Filtered by Reddit</span>';
        }
      } else if (p.status === 'undone') {
        delete urlCell.dataset.undoing;
        removeUndoingId(p.id);
        if (p.reddit_url) {
          urlCell.innerHTML = `<a href="${p.reddit_url}" target="_blank" class="text-gray-500 underline">Post Undone</a>`;
        } else {
          urlCell.innerHTML = '<span class="text-gray-500">Post Undone</span>';
        }
      } else if (p.status === 'processing') {
        urlCell.innerHTML = '<span class="text-gray-500">Processing...</span>';
      } else if (p.status === 'waiting') {
        urlCell.innerHTML = '<span class="text-gray-500">Please Wait...</span>';
      } else if (p.status === 'deleted') {
        const tooltip = p.reddit_url ? ` title="${p.reddit_url}"` : '';
        urlCell.innerHTML = `<span class="text-gray-500"${tooltip}>Deleted</span>`;
        removeUndoingId(p.id);
      } else if (p.reddit_url) {
        urlCell.innerHTML = `<a href="${p.reddit_url}" target="_blank" class="inline-flex items-center px-3 py-1 bg-indigo-500 text-white whitespace-nowrap rounded-full border border-indigo-500 hover:bg-indigo-600">See on Reddit</a>`;
      }
    }
    if (detailsBtn) {
      const postData = JSON.parse(detailsBtn.dataset.post);
      if (p.content) {
        postData.content = p.content;
      }
      if (p.reddit_url) {
        postData.reddit_url = p.reddit_url;
      }
      postData.status = p.status;
      postData.retry_count = p.retry_count;
      if (p.error_message) {
        postData.error_message = p.error_message;
      }
      detailsBtn.dataset.post = JSON.stringify(postData);
    }
    if (undoing || reposting || !['posted','failed','deleted','undone','overdue'].includes(p.status)) {
      allFinal = false;
    }
  });
  if (allFinal) {
    clearInterval(window.postStatusInterval);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const undoingIds = getUndoingIds();
  undoingIds.forEach(id => {
    const cell = document.getElementById(`reddit-url-cell-${id}`);
    if (cell) {
      cell.innerHTML = '<span class="text-gray-500">Undoing…</span>';
      cell.dataset.undoing = 'true';
    }
  });
  const repostingIds = getRepostingIds();
  repostingIds.forEach(id => {
    const cell = document.getElementById(`reddit-url-cell-${id}`);
    if (cell) {
      cell.innerHTML = '<span class="text-gray-500">Reposting…</span>';
      cell.dataset.reposting = 'true';
    }
  });
  window.postStatusInterval = setInterval(pollStatuses, 5000);
});
