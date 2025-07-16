window.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('editScheduleModal');
  const postIdInput = document.getElementById('edit-schedule-post-id');
  const timeInput = document.getElementById('new_scheduled_time');

  document.querySelectorAll('.edit-schedule-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (postIdInput) postIdInput.value = btn.dataset.postId || '';
      if (timeInput) timeInput.value = btn.dataset.scheduled || '';
      if (modal) modal.classList.remove('hidden');
    });
  });

  const cancelBtn = document.getElementById('cancelEditSchedule');
  if (cancelBtn && modal) {
    cancelBtn.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  }
});
