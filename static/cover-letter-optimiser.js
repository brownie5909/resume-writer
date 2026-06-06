console.log('Hire Ready cover-letter-optimiser.js loaded');

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
    const status = document.getElementById('clo-status');
    if (!status) return;
    status.className = `clo-status ${type || ''}`;
    status.innerHTML = escapeHtml(message || '');
  }

  function setLoading(isLoading) {
    const button = document.getElementById('clo-submit');
    if (!button) return;
    button.disabled = isLoading;
    button.innerHTML = isLoading ? 'Optimising...' : 'Optimise Cover Letter';
  }

  function renderResults(result) {
    const resultsBox = document.getElementById('clo-results');
    if (!resultsBox) return;

    const analysis = result.analysis || {};
    resultsBox.classList.add('active');
    resultsBox.innerHTML = `
      <div class="clo-card">
        <h2>Your Cover Letter Optimisation</h2>
        <div class="clo-score-grid">
          <div class="clo-score"><span>${escapeHtml(analysis.overall_score || 0)}</span><small>Overall</small></div>
          <div class="clo-score"><span>${escapeHtml(analysis.ats_score || 0)}</span><small>ATS</small></div>
          <div class="clo-score"><span>${escapeHtml(analysis.job_alignment_score || 0)}</span><small>Role Match</small></div>
        </div>
        <h3>Optimised Cover Letter</h3>
        <pre class="clo-output">${escapeHtml(result.improved_cover_letter || '')}</pre>
      </div>
    `;
    resultsBox.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function insertSavedSelector() {
    const form = document.getElementById('clo-form');
    const existing = document.getElementById('clo-saved-cover-letter');
    const firstCard = form ? form.querySelector('.clo-card') : null;

    if (!form || !firstCard || existing) return;

    const selectorWrap = document.createElement('div');
    selectorWrap.innerHTML = `
      <label class="clo-label">Use a Saved Cover Letter</label>
      <select id="clo-saved-cover-letter" class="clo-input">
        <option value="">Choose a saved cover letter, or upload/paste below</option>
      </select>
      <p style="margin:6px 0 12px;color:#667085;font-size:14px;line-height:1.45;">
        Select a previously generated or optimised cover letter to pre-fill the text below.
      </p>
    `;

    firstCard.insertBefore(selectorWrap, firstCard.firstChild);
  }

  async function loadSavedCoverLetters() {
    const select = document.getElementById('clo-saved-cover-letter');
    if (!select || !getToken()) return;

    try {
      const [generatedResponse, optimisedResponse] = await Promise.all([
        hireReadyFetch(`${API_BASE}/api/cover-letter-generator/history`),
        hireReadyFetch(`${API_BASE}/api/cover-letter-optimiser/history`)
      ]);

      const generatedData = await generatedResponse.json();
      const optimisedData = await optimisedResponse.json();
      const generated = generatedData.success ? (generatedData.results || []) : [];
      const optimised = optimisedData.success ? (optimisedData.results || []) : [];

      generated.forEach(item => {
        const option = document.createElement('option');
        option.value = `generated:${item.generation_id}`;
        option.textContent = `Generated - ${item.title || item.target_role || 'Cover Letter'}`;
        select.appendChild(option);
      });

      optimised.forEach(item => {
        const option = document.createElement('option');
        option.value = `optimised:${item.optimisation_id}`;
        option.textContent = `Optimised - ${item.title || item.target_role || 'Cover Letter'}`;
        select.appendChild(option);
      });
    } catch (error) {
      console.warn('Could not load saved cover letters', error);
    }
  }

  async function applySavedCoverLetter(event) {
    const value = event.target.value;
    if (!value) return;

    const [type, id] = value.split(':');
    const url = type === 'generated'
      ? `${API_BASE}/api/cover-letter-generator/${id}`
      : `${API_BASE}/api/cover-letter-optimiser/${id}`;

    setStatus('Loading saved cover letter...', '');

    try {
      const response = await hireReadyFetch(url);
      const data = await response.json();

      if (!response.ok || !data.success) {
        setStatus(data.error || data.detail || 'Could not load saved cover letter.', 'error');
        return;
      }

      const result = data.result || {};
      const coverLetterText = type === 'generated'
        ? result.generated_cover_letter
        : result.improved_cover_letter;

      const titleInput = document.getElementById('clo-title');
      const roleInput = document.getElementById('clo-target-role');
      const companyInput = document.getElementById('clo-company');
      const jobPostingInput = document.getElementById('clo-job-posting');
      const coverLetterInput = document.getElementById('clo-cover-letter');
      const fileInput = document.getElementById('clo-file');

      if (titleInput) titleInput.value = result.title || titleInput.value || 'Optimised Cover Letter';
      if (roleInput) roleInput.value = result.target_role || roleInput.value || '';
      if (companyInput) companyInput.value = result.company_name || companyInput.value || '';
      if (jobPostingInput) jobPostingInput.value = result.job_posting || jobPostingInput.value || '';
      if (coverLetterInput) coverLetterInput.value = coverLetterText || '';
      if (fileInput) fileInput.value = '';

      setStatus('Saved cover letter loaded. You can now review and optimise it.', 'success');
    } catch (error) {
      console.error('Saved cover letter load error:', error);
      setStatus('Could not load saved cover letter.', 'error');
    }
  }

  async function checkCanRun() {
    if (!getToken()) {
      setStatus('Please log in to use the Cover Letter Optimiser.', 'error');
      return;
    }

    try {
      const response = await hireReadyFetch(`${API_BASE}/api/cover-letter-optimiser/can-run`);
      const data = await response.json();
      if (!response.ok || !data.success) return;

      if (!data.can_run) {
        setStatus(data.message || 'Your monthly limit has been reached.', 'error');
        const upgradeBox = document.getElementById('clo-upgrade');
        if (upgradeBox) {
          upgradeBox.innerHTML = `
            <div class="clo-upgrade">
              <strong>Upgrade to Premium</strong>
              <p>${escapeHtml(data.message || 'Upgrade for unlimited cover letter optimisation.')}</p>
              <a href="/pricing/" class="clo-btn">View Pricing</a>
            </div>
          `;
        }
      }
    } catch (error) {
      console.warn('Could not check optimiser usage', error);
    }
  }

  async function optimiseCoverLetter(event) {
    event.preventDefault();

    if (!getToken()) {
      setStatus('Please log in to use the Cover Letter Optimiser.', 'error');
      return;
    }

    setLoading(true);

    try {
      const file = document.getElementById('clo-file')?.files?.[0];
      let response;

      if (file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('title', document.getElementById('clo-title')?.value || 'Optimised Cover Letter');
        formData.append('target_role', document.getElementById('clo-target-role')?.value || '');
        formData.append('company_name', document.getElementById('clo-company')?.value || '');
        formData.append('job_posting', document.getElementById('clo-job-posting')?.value || '');

        response = await hireReadyFetch(`${API_BASE}/api/cover-letter-optimiser/optimise-file`, {
          method: 'POST',
          body: formData
        });
      } else {
        const coverLetterText = document.getElementById('clo-cover-letter')?.value || '';
        if (coverLetterText.trim().length < 50) {
          setStatus('Please choose a saved cover letter, upload a file, or paste at least 50 characters.', 'error');
          return;
        }

        response = await hireReadyFetch(`${API_BASE}/api/cover-letter-optimiser/optimise`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: document.getElementById('clo-title')?.value || 'Optimised Cover Letter',
            target_role: document.getElementById('clo-target-role')?.value || null,
            company_name: document.getElementById('clo-company')?.value || null,
            job_posting: document.getElementById('clo-job-posting')?.value || null,
            cover_letter_text: coverLetterText
          })
        });
      }

      const result = await response.json();
      if (!response.ok || !result.success) {
        setStatus(result.error || result.detail || 'Optimisation failed.', 'error');
        return;
      }

      setStatus('Cover letter optimised and saved successfully.', 'success');
      renderResults(result);
    } catch (error) {
      console.error('Cover letter optimiser error:', error);
      setStatus('Something went wrong. Please try again.', 'error');
    } finally {
      setLoading(false);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('clo-form');
    if (!form) return;

    insertSavedSelector();
    document.getElementById('clo-saved-cover-letter')?.addEventListener('change', applySavedCoverLetter);
    form.addEventListener('submit', optimiseCoverLetter);
    checkCanRun();
    loadSavedCoverLetters();
  });
})();
