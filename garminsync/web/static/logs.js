// Global variables for pagination and filtering
let currentPage = 1;
const logsPerPage = 20;
let totalLogs = 0;
let currentFilters = {};

class LogsPage {
    constructor() {
        this.currentPage = 1;
        this.init();
    }
    
    init() {
        this.loadLogs();
        this.setupEventListeners();
    }
    
    async loadLogs() {
        try {
            // Build query string from filters
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: logsPerPage,
                ...currentFilters
            }).toString();

            const response = await fetch(`/api/logs?${params}`);
            if (!response.ok) {
                throw new Error('Failed to fetch logs');
            }
            
            const data = await response.json();
            totalLogs = data.total;
            this.renderLogs(data.logs);
            this.renderPagination();
        } catch (error) {
            console.error('Error loading logs:', error);
            Utils.showError('Failed to load logs: ' + error.message);
        }
    }
    
    renderLogs(logs) {
        const tbody = document.getElementById('logs-tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (!logs || logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No logs found</td></tr>';
            return;
        }
        
        logs.forEach(log => {
            const row = document.createElement('tr');
            row.className = 'row-odd'; // For alternating row colors
            
            row.innerHTML = `
                <td>${Utils.formatTimestamp(log.timestamp)}</td>
                <td>${log.operation}</td>
                <td><span class="badge badge-${log.status === 'success' ? 'success' : 
                                             log.status === 'error' ? 'error' : 
                                             'warning'}">${log.status}</span></td>
                <td>${log.message || ''}</td>
                <td>${log.activities_processed}</td>
                <td>${log.activities_downloaded}</td>
            `;
            
            tbody.appendChild(row);
        });
    }
    
    renderPagination() {
        const totalPages = Math.ceil(totalLogs / logsPerPage);
        const pagination = document.getElementById('pagination');
        if (!pagination) return;
        
        if (totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }
        
        let paginationHtml = '';
        
        // Previous button
        paginationHtml += `
            <li class="${this.currentPage === 1 ? 'disabled' : ''}">
                <a href="#" onclick="logsPage.changePage(${this.currentPage - 1}); return false;">Previous</a>
            </li>
        `;
        
        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
                paginationHtml += `
                    <li class="${i === this.currentPage ? 'active' : ''}">
                        <a href="#" onclick="logsPage.changePage(${i}); return false;">${i}</a>
                    </li>
                `;
            } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
                paginationHtml += '<li><span>...</span></li>';
            }
        }
        
        // Next button
        paginationHtml += `
            <li class="${this.currentPage === totalPages ? 'disabled' : ''}">
                <a href="#" onclick="logsPage.changePage(${this.currentPage + 1}); return false;">Next</a>
            </li>
        `;
        
        pagination.innerHTML = paginationHtml;
    }
    
    changePage(page) {
        if (page < 1 || page > Math.ceil(totalLogs / logsPerPage)) return;
        this.currentPage = page;
        this.loadLogs();
    }
    
    refreshLogs() {
        this.currentPage = 1;
        this.loadLogs();
    }
    
    applyFilters() {
        currentFilters = {
            status: document.getElementById('status-filter').value,
            operation: document.getElementById('operation-filter').value,
            date: document.getElementById('date-filter').value
        };
        
        this.currentPage = 1;
        this.loadLogs();
    }
    
    async clearLogs() {
        if (!confirm('Are you sure you want to clear all logs? This cannot be undone.')) return;
        
        try {
            const response = await fetch('/api/logs', { method: 'DELETE' });
            if (response.ok) {
                Utils.showSuccess('Logs cleared successfully');
                this.refreshLogs();
            } else {
                throw new Error('Failed to clear logs');
            }
        } catch (error) {
            console.error('Error clearing logs:', error);
            Utils.showError('Failed to clear logs: ' + error.message);
        }
    }
    
    setupEventListeners() {
        // Event listeners are handled in the global functions below
    }
}

// Initialize logs page when DOM is loaded
let logsPage;
document.addEventListener('DOMContentLoaded', function() {
    logsPage = new LogsPage();
});

// Global functions for backward compatibility with HTML onclick attributes
function changePage(page) {
    if (logsPage) logsPage.changePage(page);
}

function refreshLogs() {
    if (logsPage) logsPage.refreshLogs();
}

function applyFilters() {
    if (logsPage) logsPage.applyFilters();
}

function clearLogs() {
    if (logsPage) logsPage.clearLogs();
}
