console.log("Hire Ready dashboard-usage.js loaded");

(function () {
  const API_BASE = "https://resume-writer.onrender.com";

  function getToken() {
    return localStorage.getItem("hire_ready_token");
  }

  function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  async function hireReadyUsageFetch(url) {
    const token = getToken();

    let response = await fetch(url, {
      headers: {
        Authorization: "Bearer " + token
      }
    });

    if (response.status !== 401) {
      return response;
    }

    const refreshToken = localStorage.getItem("hire_ready_refresh_token");
    if (!refreshToken) {
      return response;
    }

    const refreshResponse = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        refresh_token: refreshToken
      })
    });

    if (!refreshResponse.ok) {
      return response;
    }

    const refreshData = await refreshResponse.json();
    localStorage.setItem("hire_ready_token", refreshData.access_token);
    localStorage.setItem("hire_ready_refresh_token", refreshData.refresh_token);
    localStorage.setItem("hire_ready_user", JSON.stringify(refreshData.user));
    localStorage.setItem("hire_ready_tier", refreshData.user.tier);

    return fetch(url, {
      headers: {
        Authorization: "Bearer " + refreshData.access_token
      }
    });
  }

  function formatLimit(item) {
    if (!item) return "Not available";
    if (item.unlimited || item.limit === null || item.limit === -1) {
      return `${item.used || 0} used · Unlimited`;
    }
    return `${item.used || 0} of ${item.limit} used`;
  }

  function createUsageRow(label, item) {
    const limitText = formatLimit(item);
    const isLimited = item && !item.unlimited && item.limit !== null && item.limit !== -1;
    const isAtLimit = isLimited && Number(item.used || 0) >= Number(item.limit || 0);

    return `
      <div style="padding:12px;border:1px solid #e4e7ec;border-radius:10px;background:#fff;">
        <strong style="display:block;color:#101828;margin-bottom:4px;">${escapeHtml(label)}</strong>
        <span style="color:${isAtLimit ? '#b42318' : '#475467'};font-weight:700;">${escapeHtml(limitText)}</span>
      </div>
    `;
  }

  function renderUsage(container, data) {
    const usage = data.usage || {};
    const tier = String(data.tier || "basic").toUpperCase();
    const showUpgrade = data.upgrade && data.upgrade.show;

    container.innerHTML = `
      <div style="margin:28px 0;padding:20px;border:1px solid #d9eaff;border-radius:16px;background:linear-gradient(135deg,#eff8ff,#ffffff);">
        <div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start;flex-wrap:wrap;margin-bottom:16px;">
          <div>
            <h2 style="margin:0 0 6px;color:#101828;">Plan & Usage</h2>
            <p style="margin:0;color:#475467;"><strong>${escapeHtml(tier)} PLAN</strong> · ${escapeHtml(data.month_year || "Current month")}</p>
          </div>
          ${showUpgrade ? `<a href="${escapeHtml(data.upgrade.url || '/pricing')}" class="resume-btn">Upgrade to Premium</a>` : ""}
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;">
          ${createUsageRow("Saved Resumes", usage.resumes)}
          ${createUsageRow("Resume Analysis", usage.resume_analysis_monthly)}
          ${createUsageRow("Version History", usage.resume_versions)}
          ${createUsageRow("PDF Downloads", usage.pdf_downloads_monthly)}
        </div>

        ${showUpgrade ? `
          <div style="margin-top:16px;padding:14px;border-radius:12px;background:#fffaeb;border:1px solid #fedf89;color:#93370d;">
            <strong>Ready to unlock more?</strong>
            <p style="margin:6px 0 0;">${escapeHtml(data.upgrade.message || "Upgrade to Premium for more features.")}</p>
          </div>
        ` : `
          <div style="margin-top:16px;padding:14px;border-radius:12px;background:#ecfdf3;border:1px solid #abefc6;color:#027a48;">
            <strong>Unlimited usage included on your current plan.</strong>
          </div>
        `}
      </div>
    `;
  }

  async function loadDashboardUsage() {
    const dashboard = document.getElementById("hire-ready-dashboard");
    if (!dashboard) return;

    const token = getToken();
    if (!token) return;

    let container = document.getElementById("dashboard-usage-summary");
    if (!container) {
      container = document.createElement("div");
      container.id = "dashboard-usage-summary";

      const actions = dashboard.querySelector(".dashboard-actions");
      if (actions && actions.parentNode) {
        actions.parentNode.insertBefore(container, actions.nextSibling);
      } else {
        dashboard.prepend(container);
      }
    }

    container.innerHTML = `
      <div style="margin:28px 0;padding:18px;border:1px solid #e4e7ec;border-radius:14px;background:#fff;color:#475467;">
        Loading plan usage...
      </div>
    `;

    try {
      const response = await hireReadyUsageFetch(`${API_BASE}/api/dashboard/usage`);
      const data = await response.json();

      if (!response.ok || !data.success) {
        container.innerHTML = "";
        console.warn("Could not load dashboard usage", data);
        return;
      }

      renderUsage(container, data);
    } catch (error) {
      console.error("Dashboard usage error:", error);
      container.innerHTML = "";
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    window.setTimeout(loadDashboardUsage, 400);
  });
})();
