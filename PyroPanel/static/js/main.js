// PyroPanel Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips, dropdowns, etc.
    initializeUI();
    
    // Set up server action buttons
    setupServerActions();
    
    // Set up real-time updates if available
    setupRealTimeUpdates();
});

/**
 * Initialize UI components
 */
function initializeUI() {
    // Add active class to current nav item
    const currentPath = window.location.pathname;
    document.querySelectorAll('nav ul li a').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
    
    // Setup mobile menu toggle if needed
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function() {
            const nav = document.querySelector('nav ul');
            nav.classList.toggle('show');
        });
    }
}

/**
 * Set up server action buttons (start, stop, restart)
 */
function setupServerActions() {
    document.querySelectorAll('.server-action').forEach(button => {
        button.addEventListener('click', async function(e) {
            e.preventDefault();
            
            const serverId = this.dataset.serverId;
            const action = this.dataset.action;
            
            if (!serverId || !action) return;
            
            try {
                // Show loading state
                this.classList.add('loading');
                this.disabled = true;
                
                // Send action request
                const response = await fetch(`/api/servers/${serverId}/action`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({ action })
                });
                
                if (!response.ok) {
                    throw new Error('Server action failed');
                }
                
                const result = await response.json();
                
                // Show success message
                showNotification('success', result.message || `Server ${action} successful`);
                
                // Update server status in UI
                updateServerStatus(serverId, action === 'stop' ? 'stopped' : 'running');
            } catch (error) {
                console.error('Error performing server action:', error);
                showNotification('error', 'Failed to perform server action');
            } finally {
                // Reset button state
                this.classList.remove('loading');
                this.disabled = false;
            }
        });
    });
}

/**
 * Update server status in the UI
 */
function updateServerStatus(serverId, status) {
    const statusElement = document.querySelector(`.server-item[data-server-id="${serverId}"] .server-status`);
    
    if (statusElement) {
        // Remove all status classes
        statusElement.classList.remove('status-running', 'status-stopped', 'status-error');
        
        // Add new status class
        statusElement.classList.add(`status-${status}`);
        
        // Update text
        statusElement.textContent = status;
    }
}

/**
 * Show notification message
 */
function showNotification(type, message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Add to document
    const notificationsContainer = document.querySelector('.notifications-container');
    if (notificationsContainer) {
        notificationsContainer.appendChild(notification);
    } else {
        // Create container if it doesn't exist
        const container = document.createElement('div');
        container.className = 'notifications-container';
        container.appendChild(notification);
        document.body.appendChild(container);
    }
    
    // Remove after delay
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

/**
 * Set up real-time updates using WebSockets if available
 */
function setupRealTimeUpdates() {
    // Check if WebSocket is supported
    if (!window.WebSocket) {
        console.log('WebSockets not supported in this browser');
        return;
    }
    
    try {
        // Connect to WebSocket server
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        const socket = new WebSocket(wsUrl);
        
        socket.onopen = function() {
            console.log('WebSocket connection established');
        };
        
        socket.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                
                // Handle different types of updates
                if (data.type === 'server_status') {
                    updateServerStatus(data.server_id, data.status);
                } else if (data.type === 'stats_update') {
                    updateResourceStats(data);
                } else if (data.type === 'notification') {
                    showNotification(data.notification_type, data.message);
                }
            } catch (error) {
                console.error('Error processing WebSocket message:', error);
            }
        };
        
        socket.onclose = function() {
            console.log('WebSocket connection closed');
            // Try to reconnect after delay
            setTimeout(setupRealTimeUpdates, 5000);
        };
        
        socket.onerror = function(error) {
            console.error('WebSocket error:', error);
        };
    } catch (error) {
        console.error('Error setting up WebSocket:', error);
    }
}

/**
 * Update resource statistics in the UI
 */
function updateResourceStats(data) {
    // Update CPU usage
    const cpuElement = document.querySelector('.cpu-usage');
    if (cpuElement && data.cpu_usage !== undefined) {
        cpuElement.textContent = `${data.cpu_usage}%`;
        
        const cpuProgress = document.querySelector('.cpu-progress');
        if (cpuProgress) {
            cpuProgress.style.width = `${data.cpu_usage}%`;
        }
    }
    
    // Update memory usage
    const memoryElement = document.querySelector('.memory-usage');
    if (memoryElement && data.memory_usage !== undefined) {
        memoryElement.textContent = `${data.memory_usage}%`;
        
        const memoryProgress = document.querySelector('.memory-progress');
        if (memoryProgress) {
            memoryProgress.style.width = `${data.memory_usage}%`;
        }
    }
    
    // Update disk usage
    const diskElement = document.querySelector('.disk-usage');
    if (diskElement && data.disk_usage !== undefined) {
        diskElement.textContent = `${data.disk_usage}%`;
        
        const diskProgress = document.querySelector('.disk-progress');
        if (diskProgress) {
            diskProgress.style.width = `${data.disk_usage}%`;
        }
    }
    
    // Update charts if they exist
    if (window.resourceChart && data.time_series) {
        // Add new data point
        window.resourceChart.data.labels.push(data.time_series.time);
        window.resourceChart.data.datasets[0].data.push(data.time_series.cpu);
        window.resourceChart.data.datasets[1].data.push(data.time_series.memory);
        
        // Remove old data points if too many
        if (window.resourceChart.data.labels.length > 20) {
            window.resourceChart.data.labels.shift();
            window.resourceChart.data.datasets[0].data.shift();
            window.resourceChart.data.datasets[1].data.shift();
        }
        
        // Update chart
        window.resourceChart.update();
    }
}
