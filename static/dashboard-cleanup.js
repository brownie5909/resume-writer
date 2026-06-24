console.log('Hire Ready dashboard-cleanup.js loaded');

(function () {
  function removeAnalysesSection() {
    const status = document.getElementById('analysis-history-status');
    const list = document.getElementById('analysis-history-list');

    if (status) status.style.display = 'none';
    if (list) list.style.display = 'none';

    Array.from(document.querySelectorAll('h2')).forEach((heading) => {
      if ((heading.textContent || '').trim() === 'My Analyses') {
        heading.style.display = 'none';
      }
    });
  }

  function updateAnalysisHeadings() {
    Array.from(document.querySelectorAll('h3')).forEach((heading) => {
      const label = (heading.textContent || '').trim();
      if (label === 'Strengths') heading.textContent = "What's Working Well";
      if (label === 'Weaknesses') heading.textContent = 'Remaining Improvement Opportunities';
      if (label === 'Specific Improvements') heading.textContent = 'Suggested Enhancements';
    });
  }

  function runCleanup() {
    removeAnalysesSection();
    updateAnalysisHeadings();
  }

  document.addEventListener('DOMContentLoaded', function () {
    setTimeout(runCleanup, 500);
    setTimeout(runCleanup, 1500);
    setInterval(updateAnalysisHeadings, 1000);
  });
})();