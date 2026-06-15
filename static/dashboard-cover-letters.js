console.log('Hire Ready dashboard-cover-letters.js loaded');

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

  function formatDate(value) {
    if (!value) return '';
    try {
      return new Date(value).toLocaleDateString();
    } catch (error) {
      return value;
    }
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

  function getCardHtml(item, type) {
    const isGenerated = type === 'generated';
    const id = isGenerated ? item.generation_id : item.optimisation_id;
    const title = item.title || (isGenerated ? 'Generated Cover Letter' : 'Optimised Cover Letter');
    const role = item.target_role || 'No role saved';
    const company = item.company_name ? ` · ${item.company_name}` : '';
    const score = item.overall_score ? `Score: ${item.overall_score}` : 'Score not available';

    return `
      <div style="border:1px solid #e4e7ec;border-radius:14px;padding:16px;background:#fff;box-shadow:0 8px 22px rgba(15,23,42,.04);">
        <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap;">
          <div>
            <strong style="display:block;color:#101828;font-size:16px;margin-bottom:4px;">${escapeHtml(title)}</strong>
            <div style="color:#475467;font-size:14px;">${escapeHtml(role + company)}</div>
            <div style="color:#667085;font-size:13px;margin-top:6px;">${escapeHtml(score)} · ${escapeHtml(formatDate(item.created_at))}</div>
          </div>
          <button type="button" class="resume-btn" onclick="window.viewHireReadyCoverLetter('${escapeHtml(type)}','${escapeHtml(id)}')">View</button>
        </div>
      </div>
    `;
  }

  function renderSection(container, generated, optimised) {
    const generatedHtml = generated.length
      ? generated.map(item => getCardHtml(item, 'generated')).join('')
      : '<p style="color:#667085;">No generated cover letters yet.</p>';

    const optimisedHtml = optimised.length
      ? optimised.map(item => getCardHtml(item, 'optimised')).join('')
      : '<p style="color:#667085;">No optimised cover letters yet.</p>';

    container.innerHTML = `
      <div style="margin:28px 0;padding:22px;border:1px solid #e4e7ec;border-radius:18px;background:#f9fafb;">
        <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:18px;">
          <div>
            <h2 style="margin:0 0 6px;color:#101828;">My Cover Letters</h2>
            <p style="margin:0;color:#667085;">Generated and optimised cover letters saved to your account.</p>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <a href="/cover-letter-generator/" class="resume-btn">Generate New</a>
            <a href="/cover-letter-optimiser/" class="resume-btn" onclick="window.location.href='/cover-letter-optimiser/'; return false;">Cover Letter Tools</a>
          </div>
        </div>

        <h3 style="margin:18px 0 10px;color:#101828;">Generated Cover Letters</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;">${generatedHtml}</div>

        <h3 style="margin:22px 0 10px;color:#101828;">Optimised Cover Letters</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;">${optimisedHtml}</div>
      </div>
    `;
  }

  function renderModal(title, content) {
    let modal = document.getElementById('hire-ready-cover-letter-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'hire-ready-cover-letter-modal';
      document.body.appendChild(modal);
    }

    modal.innerHTML = `
      <div style="position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:9998;" onclick="window.closeHireReadyCoverLetterModal()"></div>
      <div style="position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:min(880px,92vw);max-height:86vh;overflow:auto;background:#fff;border-radius:18px;padding:24px;z-index:9999;box-shadow:0 24px 70px rgba(15,23,42,.25);">
        <div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:14px;">
          <h2 style="margin:0;color:#101828;">${escapeHtml(title)}</h2>
          <button type="button" class="resume-btn" onclick="window.closeHireReadyCoverLetterModal()">Close</button>
        </div>
        <pre style="white-space:pre-wrap;font-family:Arial,sans-serif;line-height:1.55;background:#f9fafb;border:1px solid #e4e7ec;border-radius:14px;padding:16px;color:#101828;">${escapeHtml(content || '')}</pre>
      </div>
    `;
  }

  window.closeHireReadyCoverLetterModal = function () {
    const modal = document.getElementById('hire-ready-cover-letter-modal');
    if (modal) modal.remove();
  };

  window.viewHireReadyCoverLetter = async function (type, id) {
    try {
      const url = type === 'generated'
        ? `${API_BASE}/api/cover-letter-generator/${id}`
        : `${API_BASE}/api/cover-letter-optimiser/${id}`;

      const response = await hireReadyFetch(url);
      const data = await response.json();

      if (!response.ok || !data.success) {
        alert(data.detail || data.error || 'Could not load cover letter.');
        return;
      }

      const result = data.result || {};
      const title = result.title || (type === 'generated' ? 'Generated Cover Letter' : 'Optimised Cover Letter');
      const content = type === 'generated'
        ? result.generated_cover_letter
        : result.improved_cover_letter;

      renderModal(title, content);
    } catch (error) {
      console.error('Cover letter view error:', error);
      alert('Could not load cover letter.');
    }
  };

  async function loadCoverLetters() {
    const dashboard = document.getElementById('hire-ready-dashboard');
    if (!dashboard || !getToken()) return;

    let container = document.getElementById('dashboard-cover-letters');
    if (!container) {
      container = document.createElement('div');
      container.id = 'dashboard-cover-letters';
      dashboard.appendChild(container);
    }

    container.innerHTML = '<div style="margin:24px 0;padding:16px;border:1px solid #e4e7ec;border-radius:14px;background:#fff;color:#475467;">Loading cover letters...</div>';

    try {
      const [generatedResponse, optimisedResponse] = await Promise.all([
        hireReadyFetch(`${API_BASE}/api/cover-letter-generator/history`),
        hireReadyFetch(`${API_BASE}/api/cover-letter-optimiser/history`)
      ]);

      const generatedData = await generatedResponse.json();
      const optimisedData = await optimisedResponse.json();

      const generated = generatedData.success ? (generatedData.results || []) : [];
      const optimised = optimisedData.success ? (optimisedData.results || []) : [];

      renderSection(container, generated, optimised);
    } catch (error) {
      console.error('Dashboard cover letters error:', error);
      container.innerHTML = '';
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    window.setTimeout(loadCoverLetters, 800);
  });
})();
