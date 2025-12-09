/**
 * Teacher Quest Progress Management
 * Handles AJAX quest completion, dynamic updates, and filter functionality
 */

// Global error handler for unhandled promise rejections
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    // Don't prevent default - let our catch handlers deal with it
});

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    // DOM is already ready
    initialize();
}

function initialize() {
    console.log('Teacher Quest Progress JS loaded');
    
    // Initialize quest completion buttons
    initializeCompleteButtons();
    
    // Initialize start quest checkboxes
    initializeStartCheckboxes();
    
    // Initialize filter form handling
    initializeFilters();
    
    // Also try initializing after a short delay in case DOM isn't fully ready
    // But only initialize buttons that haven't been initialized yet
    setTimeout(function() {
        const uninitializedButtons = document.querySelectorAll('.complete-quest-btn:not([data-initialized])');
        console.log('Delayed check - Found uninitialized buttons:', uninitializedButtons.length);
        if (uninitializedButtons.length > 0) {
            console.log('Initializing remaining buttons after delay');
            initializeCompleteButtons();
        }
        
        // Also check for uninitialized checkboxes
        const uninitializedCheckboxes = document.querySelectorAll('.start-quest-checkbox:not([data-initialized])');
        if (uninitializedCheckboxes.length > 0) {
            console.log('Initializing remaining checkboxes after delay');
            initializeStartCheckboxes();
        }
    }, 500);
}

/**
 * Initialize start quest checkboxes with change handlers
 */
function initializeStartCheckboxes() {
    const checkboxes = document.querySelectorAll('.start-quest-checkbox:not([data-initialized])');
    
    console.log('Found start quest checkboxes to initialize:', checkboxes.length);
    
    if (checkboxes.length === 0) {
        return;
    }
    
    checkboxes.forEach((checkbox, index) => {
        // Mark as initialized to prevent duplicate listeners
        checkbox.setAttribute('data-initialized', 'true');
        
        console.log(`Initializing checkbox ${index + 1}:`, checkbox);
        checkbox.addEventListener('change', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Only process if checkbox is checked
            if (!this.checked) {
                return;
            }
            
            // Prevent multiple clicks
            if (this.disabled) {
                console.log('Checkbox already processing, ignoring change');
                return;
            }
            
            const questLogId = this.getAttribute('data-quest-log-id');
            const questTitle = this.getAttribute('data-quest-title');
            const studentName = this.getAttribute('data-student-name');
            
            console.log('Checkbox changed:', { questLogId, questTitle, studentName });
            
            if (!questLogId) {
                console.error('Missing quest-log-id attribute');
                alert('Error: Missing quest information. Please refresh the page.');
                this.checked = false;
                return;
            }
            
            // Automatically start quest
            console.log('Starting quest automatically');
            startQuest(questLogId, this);
        });
    });
}

/**
 * Start a quest via AJAX
 */
function startQuest(questLogId, checkboxElement) {
    // Disable checkbox and show loading state
    checkboxElement.disabled = true;
    const originalHTML = checkboxElement.parentElement.innerHTML;
    checkboxElement.parentElement.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Starting...';
    
    // Make AJAX request
    const url = `/teacher/quests/start/${questLogId}`;
    console.log('Making request to:', url);
    
    // Make fetch request with proper error handling
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        console.log('Response received, status:', response.status, 'Content-Type:', response.headers.get('Content-Type'));
        
        // Check if response is JSON
        const contentType = response.headers.get('Content-Type');
        if (!contentType || !contentType.includes('application/json')) {
            // Try to get text first to see what we got
            return response.text().then(text => {
                console.error('Non-JSON response:', text.substring(0, 200));
                throw new Error(`Server returned non-JSON response: ${response.status} ${response.statusText}`);
            });
        }
        
        if (!response.ok) {
            // Try to get error message from response
            return response.json().then(data => {
                throw new Error(data.error || `Server error: ${response.status}`);
            }).catch(err => {
                if (err.message && err.message.includes('Server returned')) {
                    throw err;
                }
                throw new Error(`Server error: ${response.status} ${response.statusText}`);
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Success response:', data);
        if (data.success) {
            // Update the row status
            updateQuestLogToInProgress(questLogId);
            
            // Show success message
            showMessage('success', data.message || 'Quest started successfully!');
            
            // Reload page after a short delay to show updated status
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            // Show error message
            showMessage('danger', data.error || 'Failed to start quest');
            
            // Re-enable checkbox and restore original state
            checkboxElement.disabled = false;
            checkboxElement.checked = false;
            checkboxElement.parentElement.innerHTML = originalHTML;
            checkboxElement.setAttribute('data-initialized', 'true');
            initializeStartCheckboxes();
        }
    })
    .catch(error => {
        console.error('Error starting quest:', error);
        console.error('Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
        
        // Show user-friendly error message
        let errorMessage = 'An error occurred while starting the quest. ';
        
        // Handle different error types
        if (error.name === 'FetchError' || error.name === 'TypeError') {
            errorMessage += 'Network error - please check your connection and try again.';
        } else if (error.message) {
            if (error.message.includes('Failed to fetch') || error.message.includes('network')) {
                errorMessage += 'Network error - please check your connection and try again.';
            } else if (error.message.includes('Server error')) {
                errorMessage += error.message;
            } else {
                errorMessage += error.message;
            }
        } else {
            errorMessage += 'Please try again or refresh the page.';
        }
        
        // Use alert as primary method since showMessage might not work
        alert(errorMessage);
        try {
            showMessage('danger', errorMessage);
        } catch (e) {
            console.warn('Could not show message:', e);
        }
        
        // Re-enable checkbox and restore original state
        checkboxElement.disabled = false;
        checkboxElement.checked = false;
        checkboxElement.parentElement.innerHTML = originalHTML;
        checkboxElement.setAttribute('data-initialized', 'true');
        initializeStartCheckboxes();
    });
}

/**
 * Update quest log status to IN_PROGRESS in the UI
 */
function updateQuestLogToInProgress(questLogId) {
    const row = document.querySelector(`tr[data-quest-log-id="${questLogId}"]`);
    if (!row) return;
    
    // Update status badge
    const statusCell = row.querySelector('td:nth-child(4)');
    if (statusCell) {
        statusCell.innerHTML = '<span class="badge bg-warning">In Progress</span>';
    }
    
    // Update started timestamp
    const startedCell = row.querySelector('td:nth-child(5)');
    if (startedCell) {
        const now = new Date();
        const dateStr = now.toLocaleDateString() + ' ' + now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        startedCell.innerHTML = dateStr;
    }
    
    // Update start quest column (remove checkbox)
    const startQuestCell = row.querySelector('td:nth-child(6)');
    if (startQuestCell) {
        startQuestCell.innerHTML = '<span class="text-muted">-</span>';
    }
    
    // Update actions column (add Mark Complete button)
    const actionsCell = row.querySelector('td:nth-child(7)');
    if (actionsCell) {
        const questTitle = row.getAttribute('data-quest-title') || 'Quest';
        const studentName = row.getAttribute('data-student-name') || 'Student';
        actionsCell.innerHTML = `
            <button type="button" class="btn btn-sm btn-success complete-quest-btn" 
                    data-quest-log-id="${questLogId}"
                    data-quest-title="${questTitle}"
                    data-student-name="${studentName}">
                <i class="fas fa-check me-1"></i>Mark Complete
            </button>
        `;
        // Re-initialize the complete button
        initializeCompleteButtons();
    }
}

/**
 * Initialize complete quest buttons with click handlers
 */
function initializeCompleteButtons() {
    const completeButtons = document.querySelectorAll('.complete-quest-btn:not([data-initialized])');
    
    console.log('Found complete buttons to initialize:', completeButtons.length);
    
    if (completeButtons.length === 0) {
        return;
    }
    
    completeButtons.forEach((button, index) => {
        // Mark as initialized to prevent duplicate listeners
        button.setAttribute('data-initialized', 'true');
        
        console.log(`Initializing button ${index + 1}:`, button);
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Prevent multiple clicks
            if (this.disabled) {
                console.log('Button already processing, ignoring click');
                return;
            }
            
            const questLogId = this.getAttribute('data-quest-log-id');
            const questTitle = this.getAttribute('data-quest-title');
            const studentName = this.getAttribute('data-student-name');
            
            console.log('Button clicked:', { questLogId, questTitle, studentName });
            
            if (!questLogId) {
                console.error('Missing quest-log-id attribute');
                alert('Error: Missing quest information. Please refresh the page.');
                return;
            }
            
            // Automatically complete quest without confirmation
            console.log('Completing quest automatically');
            completeQuest(questLogId, button);
        });
    });
}

/**
 * Complete a quest via AJAX
 */
function completeQuest(questLogId, buttonElement) {
    // Disable button and show loading state
    const originalHTML = buttonElement.innerHTML;
    buttonElement.disabled = true;
    buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Completing...';
    
    // Make AJAX request
    const url = `/teacher/quests/complete/${questLogId}`;
    console.log('Making request to:', url);
    
    // Make fetch request with proper error handling
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        console.log('Response received, status:', response.status, 'Content-Type:', response.headers.get('Content-Type'));
        
        // Check if response is JSON
        const contentType = response.headers.get('Content-Type');
        if (!contentType || !contentType.includes('application/json')) {
            // Try to get text first to see what we got
            return response.text().then(text => {
                console.error('Non-JSON response:', text.substring(0, 200));
                throw new Error(`Server returned non-JSON response: ${response.status} ${response.statusText}`);
            });
        }
        
        if (!response.ok) {
            // Try to get error message from response
            return response.json().then(data => {
                throw new Error(data.error || `Server error: ${response.status}`);
            }).catch(err => {
                if (err.message && err.message.includes('Server returned')) {
                    throw err;
                }
                throw new Error(`Server error: ${response.status} ${response.statusText}`);
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Success response:', data);
        if (data.success) {
            // Update the row status
            updateQuestLogStatus(questLogId, 'completed');
            
            // Reload page immediately to show updated status
            window.location.reload();
        } else {
            // Show error message (keep minimal error handling)
            showMessage('danger', data.error || 'Failed to complete quest');
            
            // Re-enable button
            buttonElement.disabled = false;
            buttonElement.innerHTML = originalHTML;
        }
    })
    .catch(error => {
        console.error('Error completing quest:', error);
        console.error('Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
        
        // Show user-friendly error message
        let errorMessage = 'An error occurred while completing the quest. ';
        
        // Handle different error types
        if (error.name === 'FetchError' || error.name === 'TypeError') {
            errorMessage += 'Network error - please check your connection and try again.';
        } else if (error.message) {
            if (error.message.includes('Failed to fetch') || error.message.includes('network')) {
                errorMessage += 'Network error - please check your connection and try again.';
            } else if (error.message.includes('Server error')) {
                errorMessage += error.message;
            } else {
                errorMessage += error.message;
            }
        } else {
            errorMessage += 'Please try again or refresh the page.';
        }
        
        // Use alert as primary method since showMessage might not work
        alert(errorMessage);
        try {
            showMessage('danger', errorMessage);
        } catch (e) {
            console.warn('Could not show message:', e);
        }
        
        // Re-enable button
        buttonElement.disabled = false;
        buttonElement.innerHTML = originalHTML;
    });
}

/**
 * Update quest log status in the UI
 */
function updateQuestLogStatus(questLogId, newStatus) {
    const row = document.querySelector(`tr[data-quest-log-id="${questLogId}"]`);
    if (!row) return;
    
    // Update status badge
    const statusCell = row.querySelector('td:nth-child(4)');
    if (statusCell) {
        let badgeClass = 'bg-secondary';
        let badgeText = 'Not Started';
        
        if (newStatus === 'completed') {
            badgeClass = 'bg-success';
            badgeText = 'Completed';
        } else if (newStatus === 'in_progress') {
            badgeClass = 'bg-warning';
            badgeText = 'In Progress';
        } else if (newStatus === 'failed') {
            badgeClass = 'bg-danger';
            badgeText = 'Failed';
        }
        
        statusCell.innerHTML = `<span class="badge ${badgeClass}">${badgeText}</span>`;
    }
    
    // Update actions cell
    const actionsCell = row.querySelector('td:nth-child(6)');
    if (actionsCell && newStatus === 'completed') {
        const now = new Date();
        const dateStr = now.toLocaleDateString() + ' ' + now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        actionsCell.innerHTML = `
            <span class="text-muted">
                <i class="fas fa-check-circle text-success me-1"></i>Completed
                <br><small>${dateStr}</small>
            </span>
        `;
    }
}

/**
 * Show a message to the user
 */
function showMessage(type, message) {
    const container = document.getElementById('messageContainer');
    const alert = document.getElementById('messageAlert');
    const text = document.getElementById('messageText');
    
    if (!container || !alert || !text) {
        // Fallback: use browser alert if elements not found
        console.warn('Message container not found, using alert()');
        window.alert(message);
        return;
    }
    
    // Set alert type and message
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    text.textContent = message;
    
    // Show container
    container.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        try {
            if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } else {
                // Fallback: just hide the element
                container.style.display = 'none';
            }
        } catch (e) {
            console.warn('Error closing alert:', e);
            container.style.display = 'none';
        }
    }, 5000);
}

/**
 * Initialize filter form handling
 */
function initializeFilters() {
    // Clear filters button
    const clearBtn = document.getElementById('clearFiltersBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', function(e) {
            e.preventDefault();
            clearFilters();
        });
    }
}

/**
 * Clear all filters and reload
 */
function clearFilters() {
    // Get the base URL from the current page
    const url = new URL(window.location.href);
    url.search = ''; // Clear all query parameters
    window.location.href = url.toString();
}

/**
 * Handle filter changes (for future enhancements)
 */
function handleFilterChange(filterType, value) {
    // This can be extended for AJAX filtering if needed
    const form = document.getElementById('filterForm');
    if (form) {
        form.submit();
    }
}

