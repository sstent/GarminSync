class HomePage {
    constructor() {
        this.logSocket = null;
        this.statsRefreshInterval = null;
        this.init();
    }
    
    init() {
        this.attachEventListeners();
        this.setupRealTimeUpdates();
        this.loadInitialData();
    }
    
    attachEventListeners() {
        const syncButton = document.getElementById('sync-now-btn');
        if (syncButton) {
            syncButton.addEventListener('click', () => this.triggerSync());
        }
    }
    
    async triggerSync() {
        const btn = document.getElementById('sync-now-btn');
        const status = document.getElementById('sync-status');
        
        if (!btn || !status) return;
        
        btn.disabled = true;
        btn.innerHTML = '<i class="icon-loading"></i> Syncing...';
        status.textContent = 'Sync in progress...';
        status.className = 'sync-status syncing';
        
        try {
            const response = await fetch('/api/sync/trigger', {method: 'POST'});
            const result = await response.json();
            
            if (response.ok) {
                status.textContent = 'Sync completed successfully';
                status.className = 'sync-status success';
                this.updateStats();
            } else {
                throw new Error(result.detail || 'Sync failed');
            }
        } catch (error) {
            status.textContent = `Sync failed: ${error.message}`;
            status.className = 'sync-status error';
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="icon-sync"></i> Sync Now';
            
            // Reset status message after 5 seconds
            setTimeout(() => {
                if (status.className.includes('success')) {
                    status.textContent = 'Ready to sync';
                    status.className = 'sync-status';
                }
            }, 5000);
        }
    }
    
    setupRealTimeUpdates() {
        // Poll for log updates every 5 seconds during active operations
        this.startLogPolling();
        
        // Update stats every 30 seconds
        this.statsRefreshInterval = setInterval(() => {
            this.updateStats();
        }, 30000);
    }
    
    async startLogPolling() {
        // For now, we'll update logs every 10 seconds
        setInterval(() => {
            this.updateLogs();
        }, 10000);
    }
    
    async updateStats() {
        try {
            const response = await fetch('/api/dashboard/stats');
            if (!response.ok) {
                throw new Error('Failed to fetch stats');
            }
            
            const stats = await response.json();
            
            const totalEl = document.getElementById('total-activities');
            const downloadedEl = document.getElementById('downloaded-activities');
            const missingEl = document.getElementById('missing-activities');
            
            if (totalEl) totalEl.textContent = stats.total;
            if (downloadedEl) downloadedEl.textContent = stats.downloaded;
            if (missingEl) missingEl.textContent = stats.missing;
        } catch (error) {
            console.error('Failed to update stats:', error);
        }
    }
    
    async updateLogs() {
        try {
            const response = await fetch('/api/status');
            if (!response.ok) {
                throw new Error('Failed to fetch logs');
            }
            
            const data = await response.json();
            this.renderLogs(data.recent_logs);
        } catch (error) {
            console.error('Failed to update logs:', error);
        }
    }
    
    renderLogs(logs) {
        const logContent = document.getElementById('log-content');
        if (!logContent) return;
        
        if (!logs || logs.length === 0) {
            logContent.innerHTML = '<div class="log-entry">No recent activity</div>';
            return;
        }
        
        const logsHtml = logs.map(log => `
            <div class="log-entry">
                <span class="timestamp">${Utils.formatTimestamp(log.timestamp)}</span>
                <span class="status ${log.status === 'success' ? 'success' : 'error'}">
                    ${log.status}
                </span>
                ${log.operation}: ${log.message || ''}
                ${log.activities_downloaded > 0 ? `Downloaded ${log.activities_downloaded} activities` : ''}
            </div>
        `).join('');
        
        logContent.innerHTML = logsHtml;
    }
    
    async loadInitialData() {
        // Load initial logs
        await this.updateLogs();
    }
}

// Initialize home page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new HomePage();
});
