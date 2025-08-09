// Auto-refresh dashboard data
setInterval(updateStatus, 30000); // Every 30 seconds

async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        // Update sync status
        const syncStatus = document.getElementById('sync-status');
        const statusBadge = data.daemon.running ? 
            '<span class="badge badge-success">Running</span>' : 
            '<span class="badge badge-danger">Stopped</span>';
        
        syncStatus.innerHTML = `${statusBadge}`;
        
        // Update daemon status
        document.getElementById('daemon-status').innerHTML = `
            <p>Status: ${statusBadge}</p>
            <p>Last Run: ${data.daemon.last_run || 'Never'}</p>
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
                ${log.activities_downloaded > 0 ? `Downloaded ${log.activities_downloaded} activities` : ''}
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

async function toggleDaemon() {
    try {
        const statusResponse = await fetch('/api/status');
        const statusData = await statusResponse.json();
        const isRunning = statusData.daemon.running;
        
        if (isRunning) {
            await fetch('/api/daemon/stop', { method: 'POST' });
            alert('Daemon stopped successfully');
        } else {
            await fetch('/api/daemon/start', { method: 'POST' });
            alert('Daemon started successfully');
        }
        
        updateStatus();
    } catch (error) {
        alert('Failed to toggle daemon: ' + error.message);
    }
}

// Schedule form handling
document.getElementById('schedule-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const enabled = document.getElementById('schedule-enabled').checked;
    const cronSchedule = document.getElementById('cron-schedule').value;
    
    try {
        const response = await fetch('/api/schedule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                enabled: enabled,
                cron_schedule: cronSchedule
            })
        });
        
        if (response.ok) {
            alert('Schedule updated successfully');
            updateStatus();
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail}`);
        }
    } catch (error) {
        alert('Failed to update schedule: ' + error.message);
    }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', updateStatus);
