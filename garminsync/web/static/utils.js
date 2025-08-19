// Utility functions for the GarminSync application

class Utils {
    // Format date for display
    static formatDate(dateStr) {
        if (!dateStr) return '-';
        return new Date(dateStr).toLocaleDateString();
    }
    
    // Format duration from seconds to HH:MM
    static formatDuration(seconds) {
        if (!seconds) return '-';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}:${minutes.toString().padStart(2, '0')}`;
    }
    
    // Format distance from meters to kilometers
    static formatDistance(meters) {
        if (!meters) return '-';
        return `${(meters / 1000).toFixed(1)} km`;
    }
    
    // Format power from watts
    static formatPower(watts) {
        return watts ? `${Math.round(watts)}W` : '-';
    }
    
    // Show error message
    static showError(message) {
        console.error(message);
        // In a real implementation, you might want to show this in the UI
        alert(`Error: ${message}`);
    }
    
    // Show success message
    static showSuccess(message) {
        console.log(message);
        // In a real implementation, you might want to show this in the UI
    }
    
    // Format timestamp for log entries
    static formatTimestamp(timestamp) {
        if (!timestamp) return '';
        return new Date(timestamp).toLocaleString();
    }
}

// Make Utils available globally
window.Utils = Utils;
