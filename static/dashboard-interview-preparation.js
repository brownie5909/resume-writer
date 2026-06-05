console.log('Hire Ready dashboard-interview-preparation.js loaded');

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

  function listHtml(items) {
    if (!Array.isArray(items) || !items.length) return '<p style="color:#667085;">No items returned.</p>';
    return `<ul style="margin-top:8px;">${items.map(item => `<li style="margin-bottom:8px;line-height:1.45;">${escapeHtml(item)}</li>`).join('')}</ul>`;
  }

  function sectionHtml(title, items) {
    return `
      <div style="background:#f9fafb;border:1px solid #e4e7ec;border-radius:14px;padding:16px;margin-bottom:14px;">
        <h3 style="margin:0 0 8px;color:#101828;">${escapeHtml(title)}</h3>
        ${listHtml(items)}
      </div>
    `;
  }

  function getCardHtml(item) {
    const title = item.title || 'Interview Preparation';
    const role = item.role_title || 'No role saved';
    const company = item.company_name ? ` · ${item.company_name}` : '';

    return `
      <div style="border:1px solid #e4e7ec;border-radius:14px;padding:16px;background:#fff;box-shadow:0 8px 22px rgba(15,23,42,.04);">
        <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap;">
          <div>
            <strong style="display:block;color:#101828;font-size:16px;margin-bottom:4px;">${escapeHtml(title)}</strong>
            <div style="color:#475467;font-size:14px;">${escapeHtml(role + company)}</div>
            <div style="color:#667085;font-size:13px;margin-top:6px;">${escapeHtml(formatDate(item.created_at))}</div>
          </div>
          <button type="button" class="resume-btn" onclick="window.viewHireReadyInterviewPrep('${escapeHtml(item.prep_id)}')">View</button>
        </div>
      </div>
    `;
  }

  function renderSection(container, items) {
    const cardsHtml = items.length
      ? items.map(getCardHtml).join('')
      : '<p style="color:#667085;">No interview preparation reports yet.</p>';

    container.innerHTML = `
      <div style="margin:28px 0;padding:22px;border:1px solid #e4e7ec;border-radius:18px;background:#f9fafb;">
        <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:18px;">
          <div>
            <h2 style="margin:0 0 6px;color:#101828;">My Interview Preparation</h2>
            <p style="margin:0;color:#667085;">Saved interview questions, employer insights and preparation tips.</p>
          </div>
          <a href="/interview-preparation/" class="resume-btn">Generate New</a>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;">${cardsHtml}</div>
      </div>
    `;
  }

  function renderModal(result) {
    const prep = result.preparation || {};
    let modal = document.getElementById('hire-ready-interview-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'hire-ready-interview-modal';
      document.body.appendChild(modal);
    }

    modal.innerHTML = `
      <div style="position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:9998;" onclick="window.closeHireReadyInterviewModal()"></div>
      <div style="position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:min(920px,92vw);max-height:86vh;overflow:auto;background:#fff;border-radius:18px;padding:24px;z-index:9999;box-shadow:0 24px 70px rgba(15,23,42,.25);">
        <div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:14px;">
          <div>
            <h2 style="margin:0;color:#101828;">${escapeHtml(result.title || 'Interview Preparation')}</h2>
            <p style="margin:6px 0 0;color:#667085;">${escapeHtml((result.role_title || '') + (result.company_name ? ' · ' + result.company_name : ''))}</p>
          </div>
          <button type="button" class="resume-btn" onclick="window.closeHireReadyInterviewModal()">Close</button>
        </div>
        ${sectionHtml('Likely Interview Questions', prep.likely_questions)}
        ${sectionHtml('Key Skills Being Assessed', prep.key_skills)}
        ${sectionHtml('What The Employer Is Looking For', prep.employer_priorities)}
        ${sectionHtml('Potential Red Flags To Avoid', prep.red_flags)}
        ${sectionHtml('Smart Questions To Ask The Interviewer', prep.questions_to_ask)}
        ${sectionHtml('Preparation Tips', prep.preparation_tips)}
      </div>
    `;
  }

  window.closeHireReadyInterviewModal = function () {
    const modal = document.getElementById('hire-ready-interview-modal');
    if (modal) modal.remove();
  };

  window.viewHireReadyInterviewPrep = async function (prepId) {
    try {
      const response = await hireReadyFetch(`${API_BASE}/api/interview-preparation/${prepId}`);
      const data = await response.json();

      if (!response.ok || !data.success) {
        alert(data.detail || data.error || 'Could not load interview preparation.');
        return;
      }

      renderModal(data.result || {});
    } catch (error) {
      console.error('Interview preparation view error:', error);
      alert('Could not load interview preparation.');
    }
  };

  async function loadInterviewPreparation() {
    const dashboard = document.getElementById('hire-ready-dashboard');
    if (!dashboard || !getToken()) return;

    let container = document.getElementById('dashboard-interview-preparation');
    if (!container) {
      container = document.createElement('div');
      container.id = 'dashboard-interview-preparation';
      dashboard.appendChild(container);
    }

    container.innerHTML = '<div style="margin:24px 0;padding:16px;border:1px solid #e4e7ec;border-radius:14px;background:#fff;color:#475467;">Loading interview preparation...</div>';

    try {
      const response = await hireReadyFetch(`${API_BASE}/api/interview-preparation/history`);
      const data = await response.json();
      const items = data.success ? (data.results || []) : [];
      renderSection(container, items);
    } catch (error) {
      console.error('Dashboard interview preparation error:', error);
      container.innerHTML = '';
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    window.setTimeout(loadInterviewPreparation, 1000);
  });
})();
