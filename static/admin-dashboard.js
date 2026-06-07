console.log('Hire Ready admin-dashboard.js loaded');

(function () {
  const API_BASE = 'https://resume-writer.onrender.com';

  function token() {
    return localStorage.getItem('hire_ready_token');
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
    return `<span class="hr-admin-pill ${tier}">${tier}</span>`;
  }

  async function loadStats() {
    const response = await api('/api/admin/stats');
    const stats = await response.json();

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

    document.getElementById('hr-admin-users').innerHTML = users.map(user => `
      <tr>
        <td>${user.full_name || ''}</td>
        <td>${user.email || ''}</td>
        <td>${tierBadge(user.tier || 'basic')}</td>
        <td>${user.is_verified ? 'Yes' : 'No'}</td>
        <td>${user.last_login || '-'}</td>
        <td>
          <div class="hr-admin-actions">
            <button class="hr-admin-btn secondary" onclick="window.hrAdminView('${user.user_id}')">View</button>
            <button class="hr-admin-btn secondary" onclick="window.hrAdminTier('${user.user_id}')">Tier</button>
          </div>
        </td>
      </tr>
    `).join('');
  }

  window.hrAdminView = async function(userId) {
    const response = await api(`/api/admin/users/${userId}`);
    const data = await response.json();

    document.getElementById('hr-admin-details').innerHTML = `
      <div class="hr-admin-details">
        <h3>${data.user.full_name}</h3>
        <p><strong>Email:</strong> ${data.user.email}</p>
        <p><strong>Tier:</strong> ${data.user.tier}</p>
        <pre>${JSON.stringify(data, null, 2)}</pre>
      </div>
    `;
  };

  window.hrAdminTier = async function(userId) {
    const tier = prompt('Enter tier: basic, premium, professional');
    if (!tier) return;

    const response = await api(`/api/admin/users/${userId}/change-tier?new_tier=${encodeURIComponent(tier)}`, {
      method: 'POST'
    });

    const result = await response.json();

    if (result.success) {
      status('Tier updated successfully', 'success');
      loadStats();
      loadUsers();
    } else {
      status(result.detail || result.error || 'Tier update failed', 'error');
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

    await loadStats();
    await loadUsers();
    status('Admin dashboard loaded.', 'success');
  }

  document.addEventListener('DOMContentLoaded', init);
})();