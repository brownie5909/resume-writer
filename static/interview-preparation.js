console.log('Hire Ready interview-preparation.js loaded');

(function () {
  const API_BASE = 'https://resume-writer.onrender.com';

  function getToken() {
    return localStorage.getItem('hire_ready_token');
  }

  function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  async function hireReadyFetch(url, options = {}) {
    const token = getToken();
    let response = await fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: 'Bearer ' + token
      }
    });

    if (response.status !== 401) return response;

    const refreshToken = localStorage.getItem('hire_ready_refresh_token');
    if (!refreshToken) return response;

    const refreshResponse = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken })
    });

    if (!refreshResponse.ok) return response;

    const refreshData = await refreshResponse.json();
    localStorage.setItem('hire_ready_token', refreshData.access_token);
    localStorage.setItem('hire_ready_refresh_token', refreshData.refresh_token);
    localStorage.setItem('hire_ready_user', JSON.stringify(refreshData.user));
    localStorage.setItem('hire_ready_tier', refreshData.user.tier);

    return fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: 'Bearer ' + refreshData.access_token
      }
    });
  }

  function setStatus(message, type) {
    const status = document.getElementById('ip-status');
    if (!status) return;
    status.className = `ip-status ${type || ''}`;
    status.innerHTML = escapeHtml(message || '');
  }

  function setLoading(isLoading) {
    const button = document.getElementById('ip-submit');
    if (!button) return;
    button.disabled = isLoading;
    button.innerHTML = isLoading ? 'Preparing...' : 'Generate Interview Prep';
  }

  function renderUpgrade(message) {
    const upgrade = document.getElementById('ip-upgrade');
    if (!upgrade) return;
    upgrade.innerHTML = `
      <div class="ip-upgrade">
        <strong>Upgrade for more interview preparation</strong>
        <p>${escapeHtml(message || 'Upgrade to Premium for unlimited interview preparation reports.')}</p>
        <a href="/pricing/" class="ip-btn">View Pricing</a>
      </div>
    `;
  }

  function listHtml(items) {
    if (!Array.isArray(items) || !items.length) return '<p>No items returned.</p>';
    return `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;
  }

  function sectionHtml(title, items) {
    return `
      <div class="ip-section">
        <h3>${escapeHtml(title)}</h3>
        ${listHtml(items)}
      </div>
    `;
  }

  function renderResults(data) {
    const results = document.getElementById('ip-results');
    if (!results) return;

    const prep = data.preparation || {};
    results.classList.add('active');
    results.innerHTML = `
      <div class="ip-card">
        <h2>Your Interview Preparation Report</h2>
        ${sectionHtml('Likely Interview Questions', prep.likely_questions)}
        ${sectionHtml('Key Skills Being Assessed', prep.key_skills)}
        ${sectionHtml('What The Employer Is Looking For', prep.employer_priorities)}
        ${sectionHtml('Potential Red Flags To Avoid', prep.red_flags)}
        ${sectionHtml('Smart Questions To Ask The Interviewer', prep.questions_to_ask)}
        ${sectionHtml('Preparation Tips', prep.preparation_tips)}
      </div>
    `;

    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  async function checkCanRun() {
    if (!getToken()) {
      setStatus('Please log in to use Interview Preparation.', 'error');
      return;
    }

    try {
      const response = await hireReadyFetch(`${API_BASE}/api/interview-preparation/can-run`);
      const data = await response.json();
      if (!response.ok || !data.success) return;
      if (!data.can_run) {
        setStatus(data.message || 'Your monthly limit has been reached.', 'error');
        renderUpgrade(data.message);
      }
    } catch (error) {
      console.warn('Could not check interview preparation usage', error);
    }
  }

  async function generateInterviewPrep(event) {
    event.preventDefault();

    if (!getToken()) {
      setStatus('Please log in to use Interview Preparation.', 'error');
      return;
    }

    const payload = {
      title: document.getElementById('ip-title')?.value || 'Interview Preparation',
      company_name: document.getElementById('ip-company')?.value || null,
      role_title: document.getElementById('ip-role')?.value || '',
      job_posting: document.getElementById('ip-job-posting')?.value || ''
    };

    if (payload.role_title.trim().length < 2) {
      setStatus('Please enter the role title.', 'error');
      return;
    }

    if (payload.job_posting.trim().length < 50) {
      setStatus('Please paste a fuller job advertisement or role description.', 'error');
      return;
    }

    setLoading(true);
    setStatus('Generating your interview preparation report...', '');

    try {
      const response = await hireReadyFetch(`${API_BASE}/api/interview-preparation/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        setStatus(data.error || data.detail || 'Interview preparation failed.', 'error');
        if (data.upgrade_required) renderUpgrade(data.message || data.error);
        return;
      }

      setStatus('Interview preparation report generated and saved successfully.', 'success');
      renderResults(data);
    } catch (error) {
      console.error('Interview preparation error:', error);
      setStatus('Something went wrong. Please try again.', 'error');
    } finally {
      setLoading(false);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('ip-form');
    if (form) {
      form.addEventListener('submit', generateInterviewPrep);
      checkCanRun();
    }
  });
})();
