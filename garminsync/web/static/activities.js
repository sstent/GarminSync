class ActivitiesPage {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 25;
        this.totalPages = 1;
        this.activities = [];
        this.filters = {};
        this.init();
    }
    
    init() {
        this.loadActivities();
        this.setupEventListeners();
    }
    
    async loadActivities() {
        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.pageSize,
                ...this.filters
            });
            
            const response = await fetch(`/api/activities?${params}`);
            if (!response.ok) {
                throw new Error('Failed to load activities');
            }
            
            const data = await response.json();
            
            this.activities = data.activities;
            this.totalPages = Math.ceil(data.total / this.pageSize);
            
            this.renderTable();
            this.renderPagination();
        } catch (error) {
            console.error('Failed to load activities:', error);
            this.showError('Failed to load activities');
        }
    }
    
    renderTable() {
        const tbody = document.getElementById('activities-tbody');
        if (!tbody) return;
        
        if (!this.activities || this.activities.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No activities found</td></tr>';
            return;
        }
        
        tbody.innerHTML = '';
        
        this.activities.forEach((activity, index) => {
            const row = this.createTableRow(activity, index);
            tbody.appendChild(row);
        });
    }
    
    createTableRow(activity, index) {
        const row = document.createElement('tr');
        row.className = index % 2 === 0 ? 'row-even' : 'row-odd';
        
        row.innerHTML = `
            <td>${Utils.formatDate(activity.start_time)}</td>
            <td>${activity.activity_type || '-'}</td>
            <td>${Utils.formatDuration(activity.duration)}</td>
            <td>${Utils.formatDistance(activity.distance)}</td>
            <td>${activity.max_heart_rate || '-'}</td>
            <td>${Utils.formatPower(activity.avg_power)}</td>
        `;
        
        return row;
    }
    
    renderPagination() {
        const pagination = document.getElementById('pagination');
        if (!pagination) return;
        
        if (this.totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }
        
        let paginationHtml = '';
        
        // Previous button
        paginationHtml += `
            <li class="${this.currentPage === 1 ? 'disabled' : ''}">
                <a href="#" onclick="activitiesPage.changePage(${this.currentPage - 1}); return false;">Previous</a>
            </li>
        `;
        
        // Page numbers
        for (let i = 1; i <= this.totalPages; i++) {
            if (i === 1 || i === this.totalPages || (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
                paginationHtml += `
                    <li class="${i === this.currentPage ? 'active' : ''}">
                        <a href="#" onclick="activitiesPage.changePage(${i}); return false;">${i}</a>
                    </li>
                `;
            } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
                paginationHtml += '<li><span>...</span></li>';
            }
        }
        
        // Next button
        paginationHtml += `
            <li class="${this.currentPage === this.totalPages ? 'disabled' : ''}">
                <a href="#" onclick="activitiesPage.changePage(${this.currentPage + 1}); return false;">Next</a>
            </li>
        `;
        
        pagination.innerHTML = paginationHtml;
    }
    
    changePage(page) {
        if (page < 1 || page > this.totalPages) return;
        this.currentPage = page;
        this.loadActivities();
    }
    
    setupEventListeners() {
        // We can add filter event listeners here if needed
    }
    
    showError(message) {
        const tbody = document.getElementById('activities-tbody');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="6">Error: ${message}</td></tr>`;
        }
    }
}

// Initialize activities page when DOM is loaded
let activitiesPage;
document.addEventListener('DOMContentLoaded', function() {
    activitiesPage = new ActivitiesPage();
});
