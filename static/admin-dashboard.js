console.log('Hire Ready admin-dashboard.js loaded');

(function () {
  const API_BASE = 'https://resume-writer.onrender.com';

  function token() {
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

  async function api(path, options = {}) {
    return fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: 'Bearer ' + token()
      }
    });
  }

  function status(message, type = '') {
    const el = document.getElementById('hr-admin-status');
    if (!el) return;
    el.className = `hr-admin-status ${type}`;
    el.textContent = message;
  }

  function tierBadge(tier) {
    const safeTier = escapeHtml(tier || 'basic');
    return `<span class="hr-admin-pill ${safeTier}">${safeTier}</span>`;
  }

  function formatDate(value) {
    if (!value) return '-';
    try {
      return new Date(value).toLocaleString();
    } catch (error) {
      return value;
    }
  }

  function renderUsageRows(items) {
    if (!Array.isArray(items) || !items.length) {
      return '<p>No usage recorded yet.</p>';
    }

    return `
      <table class="hr-admin-table">
        <thead><tr><th>Feature</th><th>Count</th><th>Month</th></tr></thead>
        <tbody>
          ${items.map(item => `
            <tr>
              <td>${escapeHtml(item.feature)}</td>
              <td>${escapeHtml(item.count)}</td>
              <td>${escapeHtml(item.month)}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }

  function renderSessionRows(items) {
    if (!Array.isArray(items) || !items.length) {
      return '<p>No recent sessions found.</p>';
    }

    return `
      <table class="hr-admin-table">
        <thead><tr><th>Created</th><th>Last Used</th><th>Active</th></tr></thead>
        <tbody>
          ${items.map(item => `
            <tr>
              <td>${escapeHtml(formatDate(item.created_at))}</td>
              <td>${escapeHtml(formatDate(item.last_used))}</td>
              <td>${item.is_active ? 'Yes' : 'No'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }

  async function loadStats() {
    const response = await api('/api/admin/stats');
    const stats = await response.json();

    if (!response.ok) {
      status(stats.detail || 'Could not load admin stats.', 'error');
      return;
    }

    document.getElementById('hr-admin-cards').innerHTML = `
      <div class="hr-admin-card"><span>Total Users</span><strong>${stats.total_users || 0}</strong></div>
      <div class="hr-admin-card"><span>Basic</span><strong>${stats.basic_users || 0}</strong></div>
      <div class="hr-admin-card"><span>Premium</span><strong>${stats.premium_users || 0}</strong></div>
      <div class="hr-admin-card"><span>Professional</span><strong>${stats.professional_users || 0}</strong></div>
      <div class="hr-admin-card"><span>Verified</span><strong>${stats.verified_users || 0}</strong></div>
      <div class="hr-admin-card"><span>Revenue</span><strong>$${stats.revenue_estimate || 0}</strong></div>
    `;
  }

  async function loadUsers(searchTerm = '') {
    const response = await api(`/api/admin/users${searchTerm ? `?search=${encodeURIComponent(searchTerm)}` : ''}`);
    const users = await response.json();

    if (!response.ok || !Array.isArray(users)) {
      status(users.detail || 'Could not load users.', 'error');
      return;
    }

    document.getElementById('hr-admin-users').innerHTML = users.map(user => `
      <tr>
        <td>${escapeHtml(user.full_name || '')}</td>
        <td>${escapeHtml(user.email || '')}</td>
        <td>${tierBadge(user.tier || 'basic')}</td>
        <td>${user.is_verified ? 'Yes' : 'No'}</td>
        <td>${escapeHtml(formatDate(user.last_login))}</td>
        <td>
          <div class="hr-admin-actions">
            <button class="hr-admin-btn secondary" onclick="window.hrAdminView('${escapeHtml(user.user_id)}')">View</button>
            <button class="hr-admin-btn secondary" onclick="window.hrAdminTier('${escapeHtml(user.user_id)}')">Tier</button>
            <button class="hr-admin-btn danger" onclick="window.hrAdminDeactivate('${escapeHtml(user.user_id)}', '${escapeHtml(user.email || '')}')">Deactivate</button>
          </div>
        </td>
      </tr>
    `).join('');
  }

  window.hrAdminView = async function(userId) {
    status('Loading user details...', '');
    const response = await api(`/api/admin/users/${userId}`);
    const data = await response.json();

    if (!response.ok || !data.user) {
      status(data.detail || 'Could not load user details.', 'error');
      return;
    }

    document.getElementById('hr-admin-details').innerHTML = `
      <div class="hr-admin-details">
        <h3>User Details</h3>
        <div class="hr-admin-grid">
          <div class="hr-admin-card"><span>Name</span><strong>${escapeHtml(data.user.full_name)}</strong></div>
          <div class="hr-admin-card"><span>Email</span><strong style="font-size:16px;word-break:break-word;">${escapeHtml(data.user.email)}</strong></div>
          <div class="hr-admin-card"><span>Tier</span><strong>${tierBadge(data.user.tier)}</strong></div>
          <div class="hr-admin-card"><span>Verified</span><strong>${data.user.is_verified ? 'Yes' : 'No'}</strong></div>
          <div class="hr-admin-card"><span>Active</span><strong>${data.user.is_active ? 'Yes' : 'No'}</strong></div>
          <div class="hr-admin-card"><span>Last Login</span><strong style="font-size:15px;">${escapeHtml(formatDate(data.user.last_login))}</strong></div>
        </div>

        <h3>Usage</h3>
        <div class="hr-admin-table-wrap">${renderUsageRows(data.usage_statistics)}</div>

        <h3>Recent Sessions</h3>
        <div class="hr-admin-table-wrap">${renderSessionRows(data.recent_sessions)}</div>
      </div>
    `;
    status('User details loaded.', 'success');
  };

  window.hrAdminTier = async function(userId) {
    const tier = prompt('Enter tier: basic, premium, professional');
    if (!tier) return;

    const normalisedTier = tier.trim().toLowerCase();
    if (!['basic', 'premium', 'professional'].includes(normalisedTier)) {
      status('Invalid tier. Use basic, premium, or professional.', 'error');
      return;
    }

    const response = await api(`/api/admin/users/${userId}/change-tier?new_tier=${encodeURIComponent(normalisedTier)}`, {
      method: 'POST'
    });

    const result = await response.json();

    if (result.success) {
      status('Tier updated successfully.', 'success');
      loadStats();
      loadUsers(document.getElementById('hr-admin-search')?.value || '');
    } else {
      status(result.detail || result.error || 'Tier update failed.', 'error');
    }
  };

  window.hrAdminDeactivate = async function(userId, email) {
    const confirmed = confirm(`Deactivate user ${email}?\n\nThey will no longer be able to log in.`);
    if (!confirmed) return;

    const response = await api(`/api/admin/users/${userId}`, { method: 'DELETE' });
    const result = await response.json();

    if (response.ok && result.success) {
      status('User deactivated successfully.', 'success');
      document.getElementById('hr-admin-details').innerHTML = '';
      loadStats();
      loadUsers(document.getElementById('hr-admin-search')?.value || '');
    } else {
      status(result.detail || result.error || 'Could not deactivate user.', 'error');
    }
  };

  async function init() {
    const mount = document.getElementById('hire-ready-admin-dashboard');
    if (!mount) return;

    mount.innerHTML = `
      <div class="hr-admin-wrap">
        <div class="hr-admin-hero">
          <h1>Admin Dashboard</h1>
          <p>Manage users, plans and platform activity.</p>
        </div>

        <div id="hr-admin-status" class="hr-admin-status">Loading admin dashboard...</div>

        <div id="hr-admin-cards" class="hr-admin-grid"></div>

        <div class="hr-admin-panel">
          <h2>Users</h2>
          <div class="hr-admin-controls">
            <input id="hr-admin-search" class="hr-admin-input" placeholder="Search users...">
            <button id="hr-admin-search-btn" class="hr-admin-btn">Search</button>
            <button id="hr-admin-refresh-btn" class="hr-admin-btn secondary">Refresh</button>
          </div>

          <div class="hr-admin-table-wrap">
            <table class="hr-admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Tier</th>
                  <th>Verified</th>
                  <th>Last Login</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="hr-admin-users"></tbody>
            </table>
          </div>

          <div id="hr-admin-details"></div>
        </div>
      </div>
    `;

    document.getElementById('hr-admin-search-btn').addEventListener('click', () => {
      loadUsers(document.getElementById('hr-admin-search').value || '');
    });

    document.getElementById('hr-admin-refresh-btn').addEventListener('click', () => {
      loadStats();
      loadUsers(document.getElementById('hr-admin-search').value || '');
      status('Admin dashboard refreshed.', 'success');
    });

    await loadStats();
    await loadUsers();
    status('Admin dashboard loaded.', 'success');
  }

  document.addEventListener('DOMContentLoaded', init);
})();
