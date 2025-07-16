// Utility function for debouncing events
function debounce(func, wait) {
  let timeout;
  return function() {
    const context = this;
    const args = arguments;
    clearTimeout(timeout);
    timeout = setTimeout(() => {
      func.apply(context, args);
    }, wait);
  };
}

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
  // Get form elements
  const form = document.querySelector('form');
  const subredditsContainer = document.getElementById('subreddits-container');
  const noSubredditsMessage = document.getElementById('no-subreddits-message');
  const addSubredditBtn = document.getElementById('add-subreddit');
  const subredditNameInput = document.getElementById('subreddit-name');
  const subredditFlairInput = document.getElementById('subreddit-flair');
  const flairSection = document.getElementById('flairSection');
  const flairLoading = document.querySelector('.flair-loading');
  const hiddenSubredditsInput = document.getElementById('subredditsJson');
  
  // Variable to track if we're editing an existing subreddit
  let editingIndex = -1;
  
  // Initialize subreddits array
  let subreddits = [];
  
  // Show the flair section when flairs are loaded via HTMX
  document.body.addEventListener('htmx:afterSwap', function(event) {
    if (event.detail.target.id === 'subreddit-flair') {
      if (flairSection) {
        flairSection.classList.remove('hidden');
      }
    }
  });
  
  // Try to load existing subreddits data
  if (hiddenSubredditsInput && hiddenSubredditsInput.value) {
    try {
      subreddits = JSON.parse(hiddenSubredditsInput.value);
      console.log('Loaded existing subreddits:', subreddits);
      renderSubreddits();
    } catch (e) {
      console.error('Error parsing subreddits JSON:', e);
    }
  }
  
  // Add input event listener with debounce to fetch flairs as user types
  subredditNameInput.addEventListener('input', debounce(function() {
    const subreddit = subredditNameInput.value.trim();
    if (subreddit.length > 2) {
      // Show flair section and fetch flairs
      if (flairSection) {
        flairSection.classList.remove('hidden');
      }
      fetchSubredditFlairs(subreddit);
    }
  }, 500));
  
  // Add click handler for the Add button
  addSubredditBtn.addEventListener('click', function() {
    addOrUpdateSubreddit();
  });
  
  // Add Enter key handler for the subreddit name input
  subredditNameInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      addOrUpdateSubreddit();
    }
  });
  
  // Form submission handler
  if (form) {
    form.addEventListener('submit', function(event) {
      // Update hidden input with current subreddits data
      updateHiddenInput();

      // Validate that we have at least one subreddit
      if (subreddits.length === 0) {
        event.preventDefault();
        if (window.toastr) {
          toastr.error('Please add at least one subreddit to the group.');
        }
        const errEl = document.getElementById('subreddits-error');
        if (errEl) {
          errEl.textContent = 'Please add at least one subreddit to the group.';
          errEl.style.display = 'block';
        }
      }
    });
  }
  
  // Function to update the hidden input with current subreddits data
  function updateHiddenInput() {
    if (hiddenSubredditsInput) {
      hiddenSubredditsInput.value = JSON.stringify(subreddits);
    }
    
    // Toggle visibility of the no subreddits message
    if (noSubredditsMessage) {
      noSubredditsMessage.style.display = subreddits.length === 0 ? 'block' : 'none';
      console.log('Updated no subreddits message visibility:', subreddits.length === 0 ? 'block' : 'none');
    }

    const errEl = document.getElementById('subreddits-error');
    if (errEl) {
      errEl.style.display = subreddits.length === 0 ? 'block' : 'none';
      if (subreddits.length === 0) {
        errEl.textContent = 'Please add at least one subreddit to the group.';
      } else {
        errEl.textContent = '';
      }
    }
  }
  
  // Function to render the subreddits list
  function renderSubreddits() {
    if (!subredditsContainer) return;
    
    // Clear current list
    subredditsContainer.innerHTML = '';
    
    // Show/hide the no subreddits message
    if (noSubredditsMessage) {
      noSubredditsMessage.style.display = subreddits.length === 0 ? 'block' : 'none';
      console.log('Rendering subreddits, count:', subreddits.length, 'message visibility:', subreddits.length === 0 ? 'block' : 'none');
    }
    
    // Add each subreddit
    subreddits.forEach((subreddit, index) => {
      const li = document.createElement('li');
      li.className = 'p-3 bg-white hover:bg-gray-50 flex justify-between items-center';
      li.setAttribute('data-index', index); // Add index as data attribute for easy reference
      
      // Subreddit info container
      const infoDiv = document.createElement('div');
      infoDiv.className = 'flex items-center'; // Add flex to align items horizontally
      
      // Subreddit name
      const subredditSpan = document.createElement('span');
      subredditSpan.className = 'text-gray-700';
      subredditSpan.textContent = `r/${subreddit.subreddit}`;
      infoDiv.appendChild(subredditSpan);
      
      // Flair badge (if present)
      if (subreddit.flair_text) {
        const flairSpan = document.createElement('span');
        flairSpan.className = 'ml-2 inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-indigo-100 text-indigo-800';
        flairSpan.textContent = subreddit.flair_text;
        infoDiv.appendChild(flairSpan);
      }
      
      li.appendChild(infoDiv);
      
      // Actions container
      const actionsDiv = document.createElement('div');
      actionsDiv.className = 'flex space-x-2';
      
      // Edit button
      const editBtn = document.createElement('button');
      editBtn.type = 'button';
      editBtn.className = 'text-blue-500 hover:text-blue-700';
      editBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>';
      editBtn.addEventListener('click', () => editSubreddit(index));
      actionsDiv.appendChild(editBtn);
      
      // Remove button
      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'text-red-500 hover:text-red-700';
      removeBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>';
      removeBtn.addEventListener('click', () => removeSubreddit(index));
      actionsDiv.appendChild(removeBtn);
      
      li.appendChild(actionsDiv);
      subredditsContainer.appendChild(li);
    });
  }
  
  // Function to fetch subreddit flairs
  function fetchSubredditFlairs(subreddit) {
    console.log(`Fetching flairs for: ${subreddit}`);
    
    // Don't try to fetch flairs if the subreddit name is empty
    if (!subreddit.trim()) {
      if (flairSection) {
        flairSection.classList.add('hidden');
      }
      return;
    }
    
    // Show loading indicator
    if (flairLoading) {
      flairLoading.classList.remove('hidden');
      if (window.showSpinner) {
        window.showSpinner(flairLoading);
      }
    }
    
    // Clear the flair badges container
    const flairBadgesContainer = document.getElementById('flair-badges-container');
    if (flairBadgesContainer) {
      flairBadgesContainer.innerHTML = '';
    }
    
    // Get the flairs using fetch - encode the subreddit parameter for URLs with special characters
    fetch(`/api/v1/reddit/flairs/${encodeURIComponent(subreddit)}`)
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to fetch flairs');
        }
        return response.json();
      })
      .then(data => {
        if (flairLoading) {
          if (window.hideSpinner) {
            window.hideSpinner(flairLoading);
          }
          flairLoading.classList.add('hidden');
        }
        
        // Clear the badges container
        if (flairBadgesContainer) {
          flairBadgesContainer.innerHTML = '';
        }
        
        // Handle custom message if present (like "No flairs needed")
        if (data.message) {
          console.log('API Message:', data.message);
          flairBadgesContainer.innerHTML = `<div class="text-blue-500">${data.message}</div>`;
          return;
        }
        
        // Handle error message if present (like "Subreddit doesn't exist")
        if (data.error) {
          console.error('API Error:', data.error);
          flairBadgesContainer.innerHTML = `<div class="text-red-500">${data.error}</div>`;
          return;
        }
        
        // Display flairs as clickable badges
        if (data.flairs && data.flairs.length > 0) {
          data.flairs.forEach(flair => {
            const badge = document.createElement('span');
            badge.className = 'inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800 mr-2 mb-2 cursor-pointer hover:bg-indigo-100';
            badge.textContent = flair.text || 'No Text';
            badge.setAttribute('data-flair-id', flair.id);
            badge.setAttribute('data-flair-text', flair.text || 'No Text');
            
            // When a badge is clicked, select it
            badge.addEventListener('click', function() {
              // Remove active class from all badges
              document.querySelectorAll('#flair-badges-container span').forEach(b => {
                b.classList.remove('bg-indigo-100', 'text-indigo-800');
                b.classList.add('bg-gray-100', 'text-gray-800');
              });
              
              // Add active class to this badge
              this.classList.remove('bg-gray-100', 'text-gray-800');
              this.classList.add('bg-indigo-100', 'text-indigo-800');
              
              // Set the hidden input value
              if (subredditFlairInput) {
                subredditFlairInput.value = this.getAttribute('data-flair-id');
              }
            });
            
            flairBadgesContainer.appendChild(badge);
            
            // If we're editing, highlight the current flair
            if (editingIndex >= 0) {
              const currentFlair = subreddits[editingIndex].flair_id;
              if (currentFlair && currentFlair === flair.id) {
                badge.click(); // Simulate a click to select this badge
              }
            }
          });
        } else {
          // No flairs found
          flairBadgesContainer.innerHTML = '<div class="text-gray-500">No flairs available for this subreddit</div>';
        }
        
        // Show the flair section
        if (flairSection) {
          flairSection.classList.remove('hidden');
        }
      })
      .catch(error => {
        console.error('Error fetching flairs:', error);
        
        if (flairLoading) {
          if (window.hideSpinner) {
            window.hideSpinner(flairLoading);
          }
          flairLoading.classList.add('hidden');
        }
        
        if (flairBadgesContainer) {
          flairBadgesContainer.innerHTML = `<div class="text-red-500">Error loading flairs: ${error.message}</div>`;
        }
        
        if (window.toastr) {
          toastr.error(`Error loading flairs: ${error.message}`);
        }
      });
  }
  
  // Function to add or update a subreddit
  function addOrUpdateSubreddit() {
    const subredditName = subredditNameInput.value.trim();
    
    // Get flair from the selected badge (badge with bg-indigo-100 class)
    const selectedBadge = document.querySelector('#flair-badges-container span.bg-indigo-100');
    const flairText = selectedBadge ? selectedBadge.getAttribute('data-flair-text') : '';
    const flairValue = selectedBadge ? selectedBadge.getAttribute('data-flair-id') : '';
    
    // Validation
    if (!subredditName) {
      if (window.toastr) {
        toastr.error('Please enter a subreddit name');
      }
      return;
    }
    
    // Check if this subreddit already exists in our list (and not the one we're editing)
    const existingIndex = subreddits.findIndex(s => 
      s.subreddit.toLowerCase() === subredditName.toLowerCase() && 
      (editingIndex === -1 || s !== subreddits[editingIndex])
    );
    
    if (existingIndex !== -1 && existingIndex !== editingIndex) {
      if (window.toastr) {
        toastr.error('This subreddit is already in your list');
      }
      return;
    }
    
    // Create the subreddit object
    const subredditObj = {
      subreddit: subredditName,
      flair_id: flairValue,
      flair_text: flairText
    };
    
    // Track if this is a new addition or an update
    const isUpdate = editingIndex !== -1;
    
    // Add or update the subreddit
    if (isUpdate) {
      // Update existing subreddit
      subreddits[editingIndex] = subredditObj;
      editingIndex = -1; // Reset editing mode
      addSubredditBtn.textContent = 'Add'; // Reset button text
    } else {
      // Add new subreddit
      subreddits.push(subredditObj);
    }
    
    // Reset form fields
    subredditNameInput.value = '';
    
    // Clear any selected badges
    document.querySelectorAll('#flair-badges-container span').forEach(badge => {
      badge.classList.remove('bg-indigo-100', 'text-indigo-800');
      badge.classList.add('bg-gray-100', 'text-gray-800');
    });
    
    // Clear hidden flair input if it exists
    if (subredditFlairInput) {
      subredditFlairInput.value = '';
    }
    
    // Clear flair text input if it exists
    const flairTextInput = document.getElementById('flair-text-input');
    if (flairTextInput) {
      flairTextInput.value = '';
    }
    
    // Clear flair badges container
    const flairBadgesContainer = document.getElementById('flair-badges-container');
    if (flairBadgesContainer) {
      flairBadgesContainer.innerHTML = '';
    }
    
    // Editing state was already reset in the update case
    
    // Hide flair section
    if (flairSection) {
      flairSection.classList.add('hidden');
    }
    
    // Show success toast notification
    if (window.toastr) {
      const msg = isUpdate ? `Updated r/${subredditName}` : `Added r/${subredditName}`;
      toastr.success(msg);
    }
    
    // Update UI
    renderSubreddits();
    updateHiddenInput();
  }
  
  // Function to edit a subreddit
  function editSubreddit(index) {
    // Set editing mode
    editingIndex = index;
    
    // Get the subreddit data
    const subreddit = subreddits[index];
    
    // Populate form fields
    subredditNameInput.value = subreddit.subreddit;
    
    // Update UI
    addSubredditBtn.textContent = 'Update';
    subredditNameInput.focus();
    
    // Show flair section
    if (flairSection) {
      flairSection.classList.remove('hidden');
    }
    
    // Fetch flairs for this subreddit
    fetchSubredditFlairs(subreddit.subreddit);
  }
  
  // Function to remove a subreddit
  function removeSubreddit(index) {
    if (index < 0 || index >= subreddits.length) return;
    
    // Use toast confirmation instead of confirm dialog
    const subredditName = subreddits[index].subreddit;
    
    // Remove the subreddit immediately without confirmation
    // If we're editing this subreddit, reset editing mode
    if (editingIndex === index) {
      editingIndex = -1;
      subredditNameInput.value = '';
      if (subredditFlairInput) {
        subredditFlairInput.innerHTML = '<option value="">-- Select a flair --</option>';
        subredditFlairInput.disabled = true;
      }
      if (flairSection) {
        flairSection.classList.add('hidden');
      }
      addSubredditBtn.textContent = 'Add';
    }
    
    // Remove the subreddit
    subreddits.splice(index, 1);
    
    // Show toast notification
    if (window.toastr) {
      toastr.info(`Removed r/${subredditName}`);
    }
    
    // Update UI
    renderSubreddits();
    updateHiddenInput();
  }
});
