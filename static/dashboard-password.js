console.log("Hire Ready dashboard-password.js loaded");

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
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  async function passwordFetch(url, options = {}) {
    const token = getToken();

    let response = await fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: "Bearer " + token,
      },
    });

    if (response.status !== 401) return response;

    const refreshToken = localStorage.getItem("hire_ready_refresh_token");
    if (!refreshToken) return response;

    const refreshResponse = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    });

    if (!refreshResponse.ok) return response;

    const refreshData = await refreshResponse.json();

    localStorage.setItem("hire_ready_token", refreshData.access_token);
    localStorage.setItem("hire_ready_refresh_token", refreshData.refresh_token);
    localStorage.setItem("hire_ready_user", JSON.stringify(refreshData.user));
    localStorage.setItem("hire_ready_tier", refreshData.user.tier);

    return fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: "Bearer " + refreshData.access_token,
      },
    });
  }

  function setStatus(message, type = "") {
    const status = document.getElementById("password-modal-status");
    if (!status) return;

    status.className = `edit-modal-status ${type}`;
    status.innerHTML = escapeHtml(message || "");
  }

  function setButtonLoading(button, isLoading) {
    if (!button) return;

    if (isLoading) {
      button.dataset.originalText = button.innerHTML;
      button.disabled = true;
      button.classList.add("loading");
      button.innerHTML = "Updating...";
    } else {
      button.disabled = false;
      button.classList.remove("loading");
      button.innerHTML = button.dataset.originalText || "Update Password";
    }
  }

  function injectPasswordModal() {
    if (document.getElementById("dashboard-password-modal")) return;

    const wrapper =
      document.querySelector(".hire-ready-dashboard-wrap") ||
      document.getElementById("hire-ready-dashboard");

    if (!wrapper) return;

    const modal = document.createElement("div");
    modal.id = "dashboard-password-modal";
    modal.className = "resume-edit-modal";
    modal.setAttribute("aria-hidden", "true");

    modal.innerHTML = `
      <div class="resume-edit-modal-backdrop" onclick="closeDashboardPasswordModal()"></div>
      <div class="resume-edit-modal-panel" role="dialog" aria-modal="true" aria-label="Change password">
        <div class="resume-edit-modal-header">
          <h2>Change Password</h2>
          <button class="resume-modal-close" onclick="closeDashboardPasswordModal()" aria-label="Close change password modal">×</button>
        </div>

        <label class="resume-edit-label" for="dashboard-current-password">Current Password</label>
        <input id="dashboard-current-password" class="resume-edit-input" type="password" autocomplete="current-password">

        <label class="resume-edit-label" for="dashboard-new-password">New Password</label>
        <input id="dashboard-new-password" class="resume-edit-input" type="password" autocomplete="new-password">
        <p class="resume-edit-help">Use at least 8 characters, including a letter and a number.</p>

        <label class="resume-edit-label" for="dashboard-confirm-password">Confirm New Password</label>
        <input id="dashboard-confirm-password" class="resume-edit-input" type="password" autocomplete="new-password">

        <p id="password-modal-status" class="edit-modal-status"></p>

        <div class="resume-edit-modal-actions">
          <button id="dashboard-password-submit" class="resume-btn" type="button">Update Password</button>
          <button class="resume-btn resume-btn-secondary" type="button" onclick="closeDashboardPasswordModal()">Cancel</button>
        </div>
      </div>
    `;

    wrapper.appendChild(modal);

    document
      .getElementById("dashboard-password-submit")
      ?.addEventListener("click", submitDashboardPasswordChange);
  }

  window.openDashboardPasswordModal = function () {
    injectPasswordModal();
    setStatus("");

    ["dashboard-current-password", "dashboard-new-password", "dashboard-confirm-password"].forEach((id) => {
      const field = document.getElementById(id);
      if (field) field.value = "";
    });

    const modal = document.getElementById("dashboard-password-modal");

    if (modal) {
      modal.classList.add("active");
      modal.setAttribute("aria-hidden", "false");
      document.body.classList.add("resume-modal-open");
    }
  };

  window.closeDashboardPasswordModal = function () {
    const modal = document.getElementById("dashboard-password-modal");

    if (modal) {
      modal.classList.remove("active");
      modal.setAttribute("aria-hidden", "true");
      document.body.classList.remove("resume-modal-open");
    }
  };

  async function submitDashboardPasswordChange() {
    const button = document.getElementById("dashboard-password-submit");
    const currentPassword = document.getElementById("dashboard-current-password")?.value || "";
    const newPassword = document.getElementById("dashboard-new-password")?.value || "";
    const confirmPassword = document.getElementById("dashboard-confirm-password")?.value || "";

    if (!currentPassword || !newPassword || !confirmPassword) {
      setStatus("Please complete all password fields.", "error");
      return;
    }

    if (newPassword !== confirmPassword) {
      setStatus("New passwords do not match.", "error");
      return;
    }

    if (newPassword.length < 8 || !/[A-Za-z]/.test(newPassword) || !/\d/.test(newPassword)) {
      setStatus("Password must be at least 8 characters and include a letter and a number.", "error");
      return;
    }

    setButtonLoading(button, true);
    setStatus("Updating password...");

    try {
      const response = await passwordFetch(`${API_BASE}/api/auth/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        setStatus(result.detail || result.error || "Could not update password.", "error");
        return;
      }

      localStorage.removeItem("hire_ready_token");
      localStorage.removeItem("hire_ready_refresh_token");
      localStorage.removeItem("hire_ready_user");
      localStorage.removeItem("hire_ready_tier");

      setStatus("Password changed. Please login again with your new password.", "success");

      window.setTimeout(() => {
        window.location.href = "/login/";
      }, 1500);
    } catch (error) {
      console.error("Change password error:", error);
      setStatus("Could not connect to the password service.", "error");
    } finally {
      setButtonLoading(button, false);
    }
  }

  function attachDashboardPasswordButton() {
    const existingForgotLink = document.querySelector('.dashboard-actions a[href="/forgot-password/"]');
    const actions = document.querySelector(".dashboard-actions");

    if (existingForgotLink) {
      existingForgotLink.href = "#";
      existingForgotLink.textContent = "Change Password";

      existingForgotLink.addEventListener("click", function (event) {
        event.preventDefault();
        window.openDashboardPasswordModal();
      });

      return;
    }

    if (actions && !document.getElementById("dashboard-change-password-btn")) {
      const button = document.createElement("button");
      button.id = "dashboard-change-password-btn";
      button.className = "resume-btn";
      button.type = "button";
      button.textContent = "Change Password";
      button.addEventListener("click", window.openDashboardPasswordModal);
      actions.appendChild(button);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    window.setTimeout(function () {
      injectPasswordModal();
      attachDashboardPasswordButton();
    }, 150);
  });
})();
