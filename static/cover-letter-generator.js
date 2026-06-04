console.log('Hire Ready cover-letter-generator.js loaded');

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
    const status = document.getElementById('clg-status');
    if (!status) return;
    status.className = `clg-status ${type || ''}`;
    status.innerHTML = escapeHtml(message || '');
  }

  function setLoading(isLoading) {
    const button = document.getElementById('clg-submit');
    if (!button) return;
    button.disabled = isLoading;
    button.innerHTML = isLoading ? 'Generating...' : 'Generate Cover Letter';
  }

  function renderUpgrade(message) {
    const upgrade = document.getElementById('clg-upgrade');
    if (!upgrade) return;
    upgrade.innerHTML = `
      <div class="clg-upgrade">
        <strong>Premium feature</strong>
        <p>${escapeHtml(message || 'Upgrade to Premium to generate tailored cover letters from scratch.')}</p>
        <a href="/pricing/" class="clg-btn">View Pricing</a>
      </div>
    `;
  }

  function renderResults(data) {
    const results = document.getElementById('clg-results');
    if (!results) return;

    const analysis = data.analysis || {};
    results.classList.add('active');
    results.innerHTML = `
      <div class="clg-card">
        <h2>Your Generated Cover Letter</h2>

        <div class="clg-score-grid">
          <div class="clg-score">
            <span>${escapeHtml(analysis.overall_score || 0)}</span>
            <small>Overall</small>
          </div>
          <div class="clg-score">
            <span>${escapeHtml(analysis.ats_score || 0)}</span>
            <small>ATS</small>
          </div>
          <div class="clg-score">
            <span>${escapeHtml(analysis.job_alignment_score || 0)}</span>
            <small>Role Match</small>
          </div>
        </div>

        <pre class="clg-output">${escapeHtml(data.cover_letter || '')}</pre>
      </div>
    `;

    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  async function checkCanRun() {
    if (!getToken()) {
      setStatus('Please log in to use the Cover Letter Generator.', 'error');
      return;
    }

    try {
      const response = await hireReadyFetch(`${API_BASE}/api/cover-letter-generator/can-run`);
      const data = await response.json();
      if (!response.ok || !data.success) return;
      if (!data.can_run) {
        setStatus(data.message || 'Upgrade required.', 'error');
        renderUpgrade(data.message);
      }
    } catch (error) {
      console.warn('Could not check generator usage', error);
    }
  }

  async function generateCoverLetter(event) {
    event.preventDefault();

    if (!getToken()) {
      setStatus('Please log in to use the Cover Letter Generator.', 'error');
      return;
    }

    const payload = {
      title: document.getElementById('clg-title')?.value || 'Generated Cover Letter',
      applicant_name: document.getElementById('clg-applicant-name')?.value || '',
      target_role: document.getElementById('clg-target-role')?.value || '',
      company_name: document.getElementById('clg-company')?.value || null,
      tone_preference: document.getElementById('clg-tone')?.value || 'professional',
      job_posting: document.getElementById('clg-job-posting')?.value || '',
      experience: document.getElementById('clg-experience')?.value || null,
      achievements: document.getElementById('clg-achievements')?.value || null
    };

    if (payload.applicant_name.trim().length < 2) {
      setStatus('Please enter the applicant name.', 'error');
      return;
    }

    if (payload.target_role.trim().length < 2) {
      setStatus('Please enter the target role.', 'error');
      return;
    }

    if (payload.job_posting.trim().length < 50) {
      setStatus('Please paste a fuller job advertisement or role description.', 'error');
      return;
    }

    setLoading(true);
    setStatus('Generating your tailored cover letter...', '');

    try {
      const response = await hireReadyFetch(`${API_BASE}/api/cover-letter-generator/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        setStatus(data.error || data.detail || 'Cover letter generation failed.', 'error');
        if (data.upgrade_required) renderUpgrade(data.message || data.error);
        return;
      }

      setStatus('Cover letter generated and saved successfully.', 'success');
      renderResults(data);
    } catch (error) {
      console.error('Cover letter generator error:', error);
      setStatus('Something went wrong. Please try again.', 'error');
    } finally {
      setLoading(false);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('clg-form');
    if (form) {
      form.addEventListener('submit', generateCoverLetter);
      checkCanRun();
    }
  });
})();
