// Auto-refresh dashboard data
setInterval(updateStatus, 30000); // Every 30 seconds

async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        // Update daemon status
        document.getElementById('daemon-status').innerHTML = `
            <p>Status: <span class="badge ${data.daemon.running ? 'badge-success' : 'badge-danger'}">
                ${data.daemon.running ? 'Running' : 'Stopped'}
            </span></p>
            <p>Next Run: ${data.daemon.next_run || 'Not scheduled'}</p>
            <p>Schedule: ${data.daemon.schedule || 'Not configured'}</p>
        `;
        
        // Update recent logs
        const logsHtml = data.recent_logs.map(log => `
            <div class="log-entry">
                <small class="text-muted">${log.timestamp}</small>
                <span class="badge badge-${log.status === 'success' ? 'success' : 'danger'}">
                    ${log.status}
                </span>
                ${log.operation}: ${log.message || ''}
            </div>
        `).join('');
        
        document.getElementById('recent-logs').innerHTML = logsHtml;
        
    } catch (error) {
        console.error('Failed to update status:', error);
    }
}

async function triggerSync() {
    try {
        await fetch('/api/sync/trigger', { method: 'POST' });
        alert('Sync triggered successfully');
        updateStatus();
    } catch (error) {
        alert('Failed to trigger sync');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', updateStatus);

async function toggleDaemon() {
    // TODO: Implement daemon toggle functionality
    alert('Daemon toggle functionality not yet implemented');
}
