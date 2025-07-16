/**
 * Main JavaScript for Reddit Group Manager
 */

document.addEventListener('DOMContentLoaded', function() {

    // Enable tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Flash message auto-close
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Handle HTMX events for UI feedback
    document.body.addEventListener('htmx:beforeRequest', function(event) {
        var target = event.detail.elt;
        if (target.classList.contains('btn')) {
            target.classList.add('disabled');
            target.setAttribute('disabled', 'disabled');
            
            // Store original text
            if (!target.dataset.originalText) {
                target.dataset.originalText = target.innerHTML;
            }
            
            // Set loading text if specified
            if (target.dataset.loadingText) {
                target.innerHTML = target.dataset.loadingText;
            }
        }
    });
    
    document.body.addEventListener('htmx:afterRequest', function(event) {
        var target = event.detail.elt;
        if (target.classList.contains('btn')) {
            target.classList.remove('disabled');
            target.removeAttribute('disabled');

            // Restore original text
            if (target.dataset.originalText) {
                target.innerHTML = target.dataset.originalText;
            }
        }

        // Global HX-Trigger handler for toast notifications
        if (event.detail.xhr) {
            var triggerHeader = event.detail.xhr.getResponseHeader('HX-Trigger');
            if (triggerHeader) {
                try {
                    var triggers = JSON.parse(triggerHeader);
                    if (triggers.toast && window.toastr) {
                        var toastData = triggers.toast;
                        var message = '';
                        var category = 'success';
                        if (typeof toastData === 'string') {
                            message = toastData;
                        } else {
                            message = toastData.message || '';
                            category = toastData.category || 'success';
                        }
                        if (typeof toastr[category] === 'function') {
                            toastr[category](message);
                        } else {
                            toastr.info(message);
                        }
                    }
                } catch (e) {
                    console.error('Invalid HX-Trigger header', triggerHeader, e);
                }
            }
        }
    });

    document.body.addEventListener('htmx:afterSwap', function(event) {
        var target = event.detail.target;
        if (target && target.classList && target.classList.contains('group-card')) {
            var cards = document.querySelectorAll('.group-card');
            if (cards.length === 0) {
                var empty = document.getElementById('no-groups');
                if (empty) {
                    empty.classList.remove('hidden');
                }
            }
        }
    });

    // Search clear button logic
    var searchInput = document.getElementById('search-input');
    var clearBtn = document.getElementById('clear-search-btn');
    if (searchInput && clearBtn) {
        var toggleClear = function() {
            if (searchInput.value.trim() === '') {
                clearBtn.classList.add('hidden');
            } else {
                clearBtn.classList.remove('hidden');
            }
        };
        searchInput.addEventListener('input', toggleClear);
        toggleClear();
        clearBtn.addEventListener('click', function() {
            searchInput.value = '';
            var form = searchInput.closest('form');
            if (form) {
                form.submit();
            }
        });
    }

    // Date range picker using Flatpickr
    var startDateInput = document.getElementById('start-date-input');
    var endDateInput = document.getElementById('end-date-input');
    var rangePickerInput = document.getElementById('date-range-picker');
    var resetDatesBtn = document.getElementById('reset-dates-btn');
    var fp;

    if (rangePickerInput && window.flatpickr) {
        var options = {
            mode: 'range',
            dateFormat: 'Y-m-d\\TH:i',
            onClose: function(selectedDates, dateStr, instance) {
                if (selectedDates.length === 2 && startDateInput && endDateInput) {
                    startDateInput.value = instance.formatDate(selectedDates[0], 'Y-m-d\\TH:i');
                    endDateInput.value = instance.formatDate(selectedDates[1], 'Y-m-d\\TH:i');
                    var form = rangePickerInput.closest('form');
                    if (form) {
                        form.submit();
                    }
                }
            }
        };
        if (startDateInput && endDateInput && startDateInput.value && endDateInput.value) {
            options.defaultDate = [startDateInput.value, endDateInput.value];
        }
        fp = flatpickr(rangePickerInput, options);
    }

    if (resetDatesBtn && rangePickerInput && startDateInput && endDateInput) {
        resetDatesBtn.addEventListener('click', function() {
            if (fp) {
                fp.clear();
            }
            rangePickerInput.value = '';
            startDateInput.value = '';
            endDateInput.value = '';
            var form = resetDatesBtn.closest('form');
            if (form) {
                form.submit();
            }
        });
    }

    // Datetime picker for scheduled posts
    var schedInput = document.getElementById('schedule_time');
    if (schedInput && window.flatpickr) {
        var schedDefault = new Date(Date.now() + 5 * 60 * 1000);
        schedDefault.setSeconds(0, 0);
        flatpickr(schedInput, {
            enableTime: true,
            dateFormat: 'Y-m-d\\TH:i',
            altInput: true,
            altFormat: 'Y-m-d H:i',
            defaultDate: schedDefault,
            minuteIncrement: 1,
            time_24hr: true
        });
    }

    var schedLabel = document.getElementById('schedule_time_label');
    if (schedLabel) {
        var tz = schedLabel.dataset.timezone;
        var fmtParts = function(date) {
            var parts = new Intl.DateTimeFormat('en-CA', {
                timeZone: tz,
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                hourCycle: 'h23'
            }).formatToParts(date);
            var map = {};
            parts.forEach(function(p) { map[p.type] = p.value; });
            return map.year + '-' + map.month + '-' + map.day + ' ' + map.hour + ':' + map.minute;
        };
        var updateLabel = function() {
            try {
                var formatted = fmtParts(new Date());
                schedLabel.textContent = 'Schedule Time (optional) - Currently: ' + tz + ' - ' + formatted;
            } catch (e) {}
        };
        updateLabel();
        setInterval(updateLabel, 60000);
    }
});
