// Main JavaScript helper for Cloud Kitchen System
document.addEventListener("DOMContentLoaded", function() {
    // Sidebar toggle for mobile devices
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", function() {
            sidebar.classList.toggle("active");
        });
    }

    // Auto-dismiss Django Alert Messages after 5 seconds
    const alerts = document.querySelectorAll(".alert-dismissible");
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});
