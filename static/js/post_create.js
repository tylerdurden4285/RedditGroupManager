/**
 * Initialize the post creation page
 * @param {Array} groups - List of available groups
 * @param {Array} [testSubreddits] - Optional list of test subreddits
 */
function initPostCreatePage(groups, testSubreddits = []) {
    console.log('Initializing post creation page');

    // DOM elements
    const postTypeSelect = document.getElementById('post_type');
    const groupContainer = document.getElementById('group-container');
    const subredditContainer = document.getElementById('subreddit-container');
    const groupSelect = document.getElementById('group_id');
    const subredditSelect = document.getElementById('subreddit');
    const flairContainer = document.getElementById('flair-container');
    const flairSelect = document.getElementById('flair_id');
    const flairLoading = document.getElementById('flair-loading');
    const loadFlairsBtn = document.getElementById('loadFlairsBtn');
    
    // Initialize Select2 for select elements
    $(groupSelect).select2({
        placeholder: 'Select a group',
        width: '100%'
    });
    
    $(subredditSelect).select2({
        placeholder: 'Select a subreddit',
        width: '100%'
    });
    
    // Toggle between group and subreddit based on post type
    postTypeSelect.addEventListener('change', function() {
        if (this.value === 'group') {
            groupContainer.classList.remove('hidden');
            subredditContainer.classList.add('hidden');
            flairContainer.classList.add('hidden');
        } else {
            groupContainer.classList.add('hidden');
            subredditContainer.classList.remove('hidden');
            
            // Populate the subreddit dropdown with test subreddits
            populateSubreddits(testSubreddits);
        }
    });
    
    // Handle subreddit change to fetch flairs
    subredditSelect.addEventListener('change', function() {
        const subreddit = this.value;
        if (subreddit) {
            if (loadFlairsBtn) loadFlairsBtn.disabled = false;
            fetchFlairs(subreddit, loadFlairsBtn);
        } else {
            flairContainer.classList.add('hidden');
            if (loadFlairsBtn) loadFlairsBtn.disabled = true;
        }
    });

    if (loadFlairsBtn) {
        loadFlairsBtn.addEventListener('click', function() {
            const subreddit = subredditSelect.value;
            if (subreddit) {
                fetchFlairs(subreddit, loadFlairsBtn);
            }
        });
    }
    
    // Populate subreddits dropdown
    function populateSubreddits(subreddits) {
        // Clear existing options except the first placeholder
        while (subredditSelect.options.length > 1) {
            subredditSelect.remove(1);
        }
        
        // Add test subreddits
        subreddits.forEach(subreddit => {
            const option = document.createElement('option');
            option.value = subreddit;
            option.textContent = subreddit;
            subredditSelect.appendChild(option);
        });
        
        // Refresh Select2
        $(subredditSelect).trigger('change');
    }
    
    // Fetch flairs for a subreddit
    function fetchFlairs(subreddit, triggerBtn) {
        // Show loading indicator
        flairContainer.classList.remove('hidden');
        if (flairLoading && window.showSpinner) {
            flairLoading.style.display = 'block';
            window.showSpinner(flairLoading);
        }
        flairSelect.innerHTML = '<option value="">Loading flairs...</option>';
        flairSelect.disabled = true;
        if (triggerBtn && window.showSpinner) {
            window.showSpinner(triggerBtn);
        }
        
        // Fetch flairs from API
        fetch(`/api/v1/reddit/flairs/${subreddit}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Clear existing options
                flairSelect.innerHTML = '';
                
                // Add a placeholder option
                const placeholderOption = document.createElement('option');
                placeholderOption.value = '';
                placeholderOption.textContent = '-- Select a flair (optional) --';
                flairSelect.appendChild(placeholderOption);
                
                // Add flairs
                if (Array.isArray(data) && data.length > 0) {
                    data.forEach(flair => {
                        const option = document.createElement('option');
                        option.value = flair.id;
                        option.textContent = flair.text;
                        flairSelect.appendChild(option);
                    });
                    flairSelect.disabled = false;
                } else {
                    const noFlairsOption = document.createElement('option');
                    noFlairsOption.value = '';
                    noFlairsOption.textContent = 'No flairs available';
                    flairSelect.appendChild(noFlairsOption);
                    flairSelect.disabled = true;
                }
            })
            .catch(error => {
                console.error('Error fetching flairs:', error);
                flairSelect.innerHTML = '';
                const errorOption = document.createElement('option');
                errorOption.value = '';
                errorOption.textContent = 'Error loading flairs';
                flairSelect.appendChild(errorOption);
                flairSelect.disabled = true;
            })
            .finally(() => {
                if (flairLoading && window.hideSpinner) {
                    window.hideSpinner(flairLoading);
                    flairLoading.style.display = 'none';
                }
                if (triggerBtn && window.hideSpinner) {
                    window.hideSpinner(triggerBtn);
                }
            });
    }
    
    // Initialize the page
    if (postTypeSelect.value === 'group') {
        groupContainer.classList.remove('hidden');
        subredditContainer.classList.add('hidden');
    } else {
        groupContainer.classList.add('hidden');
        subredditContainer.classList.remove('hidden');
        populateSubreddits(testSubreddits);
    }

    if (loadFlairsBtn) {
        loadFlairsBtn.disabled = !subredditSelect.value;
    }
}
