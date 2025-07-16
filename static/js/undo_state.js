function getUndoingIds() {
  try {
    return JSON.parse(sessionStorage.getItem('undoingIds') || '[]');
  } catch (e) {
    return [];
  }
}

function addUndoingId(id) {
  const ids = getUndoingIds();
  if (!ids.includes(id)) {
    ids.push(id);
    sessionStorage.setItem('undoingIds', JSON.stringify(ids));
  }
}

function removeUndoingId(id) {
  const ids = getUndoingIds().filter(x => x !== id);
  sessionStorage.setItem('undoingIds', JSON.stringify(ids));
}
