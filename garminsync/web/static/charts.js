// Initialize the activity progress chart
document.addEventListener('DOMContentLoaded', function() {
    // Fetch activity stats from the API
    fetch('/api/activities/stats')
        .then(response => response.json())
        .then(data => {
            // Create doughnut chart
            const ctx = document.getElementById('activityChart').getContext('2d');
            const chart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Downloaded', 'Missing'],
                    datasets: [{
                        data: [data.downloaded, data.missing],
                        backgroundColor: ['#28a745', '#dc3545'],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: true,
                            text: 'Activity Status'
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error fetching activity stats:', error);
        });
});
