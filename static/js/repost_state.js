function getRepostingIds() {
  try {
    return JSON.parse(sessionStorage.getItem('repostingIds') || '[]');
  } catch (e) {
    return [];
  }
}

function addRepostingId(id) {
  const ids = getRepostingIds();
  if (!ids.includes(id)) {
    ids.push(id);
    sessionStorage.setItem('repostingIds', JSON.stringify(ids));
  }
}

function removeRepostingId(id) {
  const ids = getRepostingIds().filter(x => x !== id);
  sessionStorage.setItem('repostingIds', JSON.stringify(ids));
}
