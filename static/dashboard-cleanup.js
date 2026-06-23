console.log('Hire Ready dashboard-cleanup.js loaded');

(function () {
  function removeAnalysesSection() {
    const status = document.getElementById('analysis-history-status');
    const list = document.getElementById('analysis-history-list');

    if (status) status.style.display = 'none';
    if (list) list.style.display = 'none';

    const headings = Array.from(document.querySelectorAll('h2'));
    headings.forEach((heading) => {
      if ((heading.textContent || '').trim() === 'My Analyses') {
        heading.style.display = 'none';
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    setTimeout(removeAnalysesSection, 500);
    setTimeout(removeAnalysesSection, 1500);
  });
})();