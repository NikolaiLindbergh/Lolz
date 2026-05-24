// Sidebar toggle
const toggleBtn = document.getElementById('sidebarToggle');
const sidebar = document.getElementById('sidebar');
const content = document.getElementById('page-content-wrapper');

if (toggleBtn) {
  toggleBtn.addEventListener('click', () => {
    if (window.innerWidth < 769) {
      sidebar.classList.toggle('mobile-open');
    } else {
      sidebar.classList.toggle('collapsed');
      content.classList.toggle('expanded');
    }
  });
}

// Auto-dismiss alerts after 4 seconds
document.querySelectorAll('.alert.alert-success, .alert.alert-info').forEach(el => {
  setTimeout(() => {
    const bsAlert = new bootstrap.Alert(el);
    bsAlert.close();
  }, 4000);
});

// Loading state on AI analyze button
const analyzeBtn = document.getElementById('analyzeBtn');
if (analyzeBtn) {
  analyzeBtn.closest('form').addEventListener('submit', () => {
    analyzeBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Analyzing… Please wait';
    analyzeBtn.disabled = true;
  });
}
