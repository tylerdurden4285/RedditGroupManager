// Handle selecting posts and updating delete button
window.addEventListener('DOMContentLoaded', () => {
  const deleteBtn = document.getElementById('deleteHistoryDropdownButton');
  const dropdown = document.getElementById('deleteHistoryDropdownMenu');
  const arrow = deleteBtn.querySelector('svg');
  const arrowHTML = arrow ? arrow.outerHTML : '';
  const modal = document.getElementById('deleteHistoryModal');
  const deleteForm = document.getElementById('deleteHistoryForm');
  const deleteMsg = document.getElementById('deleteHistoryModalMessage');
  const deleteIdsInput = document.getElementById('delete-post-ids');
  const undoBtn = document.getElementById('undoSelectedButton');
  const undoModal = document.getElementById('undoSelectedModal');
  const undoForm = document.getElementById('undoSelectedForm');
  const undoMsg = document.getElementById('undoSelectedModalMessage');
  const undoIdsInput = document.getElementById('undo-post-ids');
  const editBtn = document.getElementById('editSelectedButton');
  const editModal = document.getElementById('editScheduleModal');
  const editForm = document.getElementById('editScheduleForm');
  const editIdsInput = document.getElementById('edit-schedule-ids');
  const editInput = document.getElementById('edit-schedule-input');
  const cancelEdit = document.getElementById('cancelEditSchedule');
  let editPicker = null;
  if (editInput && window.flatpickr) {
    editPicker = flatpickr(editInput, {
      enableTime: true,
      dateFormat: 'Y-m-d\\TH:i',
      altInput: true,
      altFormat: 'Y-m-d H:i',
      defaultDate: new Date(Date.now() + 5 * 60 * 1000),
      minuteIncrement: 1,
      time_24hr: true
    });
  }
  const repostBtn = document.getElementById('repostSelectedButton');
  const repostModal = document.getElementById('repostSelectedModal');
  const repostForm = document.getElementById('repostSelectedForm');
  const repostMsg = document.getElementById('repostSelectedModalMessage');
  const repostIdsInput = document.getElementById('repost-post-ids');
  const selectAll = document.getElementById('select-all-checkbox');
  const checkboxes = document.querySelectorAll('.post-select-checkbox');

  function updateButtons() {
    const checked = document.querySelectorAll('.post-select-checkbox:checked');
    const count = checked.length;
    if (count > 0) {
      deleteBtn.innerHTML = `Delete (${count})`;
      if (dropdown) dropdown.classList.add('hidden');
      let allPosted = true;
      let allUndone = true;
      let allScheduled = true;
      checked.forEach(cb => {
        const span = document.getElementById(`status-span-${cb.value}`);
        const status = span ? span.textContent.trim() : '';
        if (status !== 'posted') {
          allPosted = false;
        }
        if (status !== 'undone') {
          allUndone = false;
        }
        if (status !== 'scheduled' && status !== 'overdue') {
          allScheduled = false;
        }
      });
      if (undoBtn) {
        if (allPosted) {
          undoBtn.classList.remove('hidden');
          undoBtn.textContent = `Undo (${count})`;
        } else {
          undoBtn.classList.add('hidden');
        }
      }
      if (repostBtn) {
        if (allUndone) {
          repostBtn.classList.remove('hidden');
          repostBtn.textContent = `Repost (${count})`;
        } else {
          repostBtn.classList.add('hidden');
        }
      }
      if (editBtn) {
        if (allScheduled) {
          editBtn.classList.remove('hidden');
          editBtn.textContent = `Edit (${count})`;
        } else {
          editBtn.classList.add('hidden');
        }
      }
    } else {
      deleteBtn.innerHTML = `Clean Posts ${arrowHTML}`;
      if (undoBtn) undoBtn.classList.add('hidden');
      if (repostBtn) repostBtn.classList.add('hidden');
      if (editBtn) editBtn.classList.add('hidden');
    }
  }

  if (selectAll) {
    selectAll.addEventListener('change', () => {
      checkboxes.forEach(cb => { cb.checked = selectAll.checked; });
      updateButtons();
    });
  }

  checkboxes.forEach(cb => cb.addEventListener('change', updateButtons));

  if (deleteBtn && modal) {
    deleteBtn.addEventListener('click', () => {
      const checked = document.querySelectorAll('.post-select-checkbox:checked');
      if (checked.length > 0) {
        const ids = Array.from(checked).map(c => c.value).join(',');
        deleteForm.action = '/posts/delete-selected';
        deleteIdsInput.value = ids;
        deleteMsg.textContent = `Delete ${checked.length} selected posts?`;
        modal.classList.remove('hidden');
      } else if (dropdown) {
        dropdown.classList.toggle('hidden');
      }
    });
  }

  if (dropdown) {
    document.addEventListener('click', evt => {
      if (!deleteBtn.contains(evt.target) && !dropdown.contains(evt.target)) {
        dropdown.classList.add('hidden');
      }
    });
  }

  if (undoBtn && undoModal) {
    undoBtn.addEventListener('click', () => {
      const checked = document.querySelectorAll('.post-select-checkbox:checked');
      if (checked.length > 0) {
        const ids = Array.from(checked).map(c => c.value).join(',');
        undoForm.action = '/posts/undo-selected';
        undoIdsInput.value = ids;
        undoMsg.textContent = `Undo ${checked.length} selected posts?`;
        undoModal.classList.remove('hidden');
      }
    });
  }

  if (repostBtn && repostModal) {
    repostBtn.addEventListener('click', () => {
      const checked = document.querySelectorAll('.post-select-checkbox:checked');
      if (checked.length > 0) {
        const ids = Array.from(checked).map(c => c.value).join(',');
        repostForm.action = '/posts/repost-selected';
        repostIdsInput.value = ids;
        repostMsg.textContent = `Repost ${checked.length} selected posts?`;
        repostModal.classList.remove('hidden');
      }
    });
  }

  if (editBtn && editModal) {
    editBtn.addEventListener('click', () => {
      const checked = document.querySelectorAll('.post-select-checkbox:checked');
      if (checked.length > 0) {
        const ids = Array.from(checked).map(c => c.value).join(',');
        editForm.action = '/posts/edit-scheduled';
        editIdsInput.value = ids;
        const dt = checked[0].dataset.scheduled;
        if (dt && editPicker) {
          editPicker.setDate(dt);
        }
        editModal.classList.remove('hidden');
      }
    });
  }

  if (cancelEdit && editModal) {
    cancelEdit.addEventListener('click', () => {
      editModal.classList.add('hidden');
    });
  }

  if (undoForm) {
    undoForm.addEventListener('submit', evt => {
      evt.preventDefault();
      const ids = undoIdsInput.value.split(',').filter(id => id);
      ids.forEach(id => {
        const cell = document.getElementById(`reddit-url-cell-${id}`);
        if (cell) {
          cell.innerHTML = '<span class="text-gray-500">Undoing…</span>';
          cell.dataset.undoing = 'true';
        }
        addUndoingId(parseInt(id, 10));
      });
      if (window.showPageSpinner) {
        window.showPageSpinner();
      }
      undoForm.submit();
    });
  }

  if (repostForm) {
    repostForm.addEventListener('submit', evt => {
      evt.preventDefault();
      const ids = repostIdsInput.value.split(',').filter(id => id);
      ids.forEach(id => {
        const cell = document.getElementById(`reddit-url-cell-${id}`);
        if (cell) {
          cell.innerHTML = '<span class="text-gray-500">Reposting…</span>';
          cell.dataset.reposting = 'true';
        }
        addRepostingId(parseInt(id, 10));
      });
      if (repostBtn) repostBtn.classList.add('hidden');
      if (window.showPageSpinner) {
        window.showPageSpinner();
      }
      repostForm.submit();
    });
  }

  updateButtons();
});
