class Navigation {
    constructor() {
        this.currentPage = this.getCurrentPage();
        this.render();
    }
    
    getCurrentPage() {
        return window.location.pathname === '/activities' ? 'activities' : 'home';
    }
    
    render() {
        const nav = document.querySelector('.navigation');
        if (nav) {
            nav.innerHTML = this.getNavigationHTML();
            this.attachEventListeners();
        }
    }
    
    getNavigationHTML() {
        return `
            <nav class="nav-tabs">
                <button class="nav-tab ${this.currentPage === 'home' ? 'active' : ''}" 
                        data-page="home">Home</button>
                <button class="nav-tab ${this.currentPage === 'activities' ? 'active' : ''}" 
                        data-page="activities">Activities</button>
            </nav>
        `;
    }
    
    attachEventListeners() {
        const tabs = document.querySelectorAll('.nav-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const page = e.target.getAttribute('data-page');
                this.navigateToPage(page);
            });
        });
    }
    
    navigateToPage(page) {
        if (page === 'home') {
            window.location.href = '/';
        } else if (page === 'activities') {
            window.location.href = '/activities';
        }
    }
}

// Initialize navigation when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new Navigation();
});
