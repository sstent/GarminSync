// Global variables for pagination and filtering
let currentPage = 1;
const logsPerPage = 20;
let totalLogs = 0;
let currentFilters = {};

// Initialize logs page
document.addEventListener('DOMContentLoaded', function() {
    loadLogs();
});

async function loadLogs() {
    try {
        // Build query string from filters
        const params = new URLSearchParams({
            page: currentPage,
            perPage: logsPerPage,
            ...currentFilters
        }).toString();

        const response = await fetch(`/api/logs?${params}`);
        if (!response.ok) {
            throw new Error('Failed to fetch logs');
        }
        
        const data = await response.json();
        totalLogs = data.total;
        renderLogs(data.logs);
        renderPagination();
    } catch (error) {
        console.error('Error loading logs:', error);
        alert('Failed to load logs: ' + error.message);
    }
}

function renderLogs(logs) {
    const tbody = document.getElementById('logs-tbody');
    tbody.innerHTML = '';
    
    logs.forEach(log => {
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${log.timestamp}</td>
            <td>${log.operation}</td>
            <td><span class="badge badge-${log.status === 'success' ? 'success' : 
                                         log.status === 'error' ? 'danger' : 
                                         'warning'}">${log.status}</span></td>
            <td>${log.message || ''}</td>
            <td>${log.activities_processed}</td>
            <td>${log.activities_downloaded}</td>
        `;
        
        tbody.appendChild(row);
    });
}

function renderPagination() {
    const totalPages = Math.ceil(totalLogs / logsPerPage);
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';
    
    // Previous button
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `<a class="page-link" href="#" onclick="changePage(${currentPage - 1})">Previous</a>`;
    pagination.appendChild(prevLi);
    
    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${i === currentPage ? 'active' : ''}`;
        li.innerHTML = `<a class="page-link" href="#" onclick="changePage(${i})">${i}</a>`;
        pagination.appendChild(li);
    }
    
    // Next button
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    nextLi.innerHTML = `<a class="page-link" href="#" onclick="changePage(${currentPage + 1})">Next</a>`;
    pagination.appendChild(nextLi);
}

function changePage(page) {
    if (page < 1 || page > Math.ceil(totalLogs / logsPerPage)) return;
    currentPage = page;
    loadLogs();
}

function refreshLogs() {
    currentPage = 1;
    loadLogs();
}

function applyFilters() {
    currentFilters = {
        status: document.getElementById('status-filter').value,
        operation: document.getElementById('operation-filter').value,
        date: document.getElementById('date-filter').value
    };
    
    currentPage = 1;
    loadLogs();
}

async function clearLogs() {
    if (!confirm('Are you sure you want to clear all logs? This cannot be undone.')) return;
    
    try {
        const response = await fetch('/api/logs', { method: 'DELETE' });
        if (response.ok) {
            alert('Logs cleared successfully');
            refreshLogs();
        } else {
            throw new Error('Failed to clear logs');
        }
    } catch (error) {
        console.error('Error clearing logs:', error);
        alert('Failed to clear logs: ' + error.message);
    }
}
