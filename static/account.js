console.log("Hire Ready account.js loaded");

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

  async function accountFetch(path, options = {}) {
    const token = getToken();

    return fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: "Bearer " + token
      }
    });
  }

  function setStatus(message, type = "") {
    const status = document.getElementById("hr-account-status");
    if (!status) return;

    status.className = `hr-account-status ${type}`;
    status.textContent = message;
  }

  function renderAccount(user) {
    const mount = document.getElementById("hire-ready-account");

    const tier = user.tier || "basic";

    mount.innerHTML = `
      <section class="hr-account-wrap">

        <div class="hr-account-hero">
          <h1>Account Settings</h1>
          <p>Manage your account information and security settings.</p>
        </div>

        <div class="hr-account-grid">

          <div class="hr-account-card">
            <h2>Account Details</h2>

            <div class="hr-account-row">
              <span class="hr-account-label">Name</span>
              <span class="hr-account-value">${escapeHtml(user.full_name || "")}</span>
            </div>

            <div class="hr-account-row">
              <span class="hr-account-label">Email</span>
              <span class="hr-account-value">${escapeHtml(user.email || "")}</span>
            </div>

            <div class="hr-account-row">
              <span class="hr-account-label">Plan</span>
              <span class="hr-account-value">
                <span class="hr-account-pill ${tier}">
                  ${escapeHtml(tier)}
                </span>
              </span>
            </div>

            <div class="hr-account-actions">
              <a href="/dashboard/" class="hr-account-btn secondary">
                Back To Dashboard
              </a>

              <a href="/pricing/" class="hr-account-btn secondary">
                View Plans
              </a>
            </div>
          </div>

          <div class="hr-account-card">

            <h2>Change Password</h2>

            <label>Current Password</label>
            <input
              id="hr-current-password"
              class="hr-account-input"
              type="password"
            >

            <label>New Password</label>
            <input
              id="hr-new-password"
              class="hr-account-input"
              type="password"
            >

            <p class="hr-account-help">
              Use at least 8 characters including a letter and a number.
            </p>

            <label>Confirm Password</label>
            <input
              id="hr-confirm-password"
              class="hr-account-input"
              type="password"
            >

            <div class="hr-account-actions">
              <button
                id="hr-change-password-btn"
                class="hr-account-btn"
              >
                Update Password
              </button>
            </div>

          </div>

          <div class="hr-account-card">

            <h2>Subscription</h2>

            <div class="hr-account-row">
              <span class="hr-account-label">Current Plan</span>
              <span class="hr-account-value">
                ${escapeHtml(tier)}
              </span>
            </div>

            <div class="hr-account-note">
              Subscription management and billing portal integration
              will be added in the next release.
            </div>

            <div class="hr-account-actions">
              <a href="/pricing/" class="hr-account-btn">
                Upgrade Plan
              </a>
            </div>

          </div>

        </div>

        <div id="hr-account-status" class="hr-account-status"></div>

      </section>
    `;

    document
      .getElementById("hr-change-password-btn")
      .addEventListener("click", changePassword);
  }

  async function changePassword() {

    const currentPassword =
      document.getElementById("hr-current-password").value;

    const newPassword =
      document.getElementById("hr-new-password").value;

    const confirmPassword =
      document.getElementById("hr-confirm-password").value;

    if (!currentPassword || !newPassword || !confirmPassword) {
      setStatus("Please complete all password fields.", "error");
      return;
    }

    if (newPassword !== confirmPassword) {
      setStatus("New passwords do not match.", "error");
      return;
    }

    try {

      const response = await accountFetch(
        "/api/auth/change-password",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword
          })
        }
      );

      const result = await response.json();

      if (!response.ok) {
        setStatus(
          result.detail || "Password update failed.",
          "error"
        );
        return;
      }

      setStatus(
        "Password updated successfully. Please login again.",
        "success"
      );

      localStorage.removeItem("hire_ready_token");
      localStorage.removeItem("hire_ready_refresh_token");

      setTimeout(() => {
        window.location.href = "/login/";
      }, 1500);

    } catch (error) {

      console.error(error);

      setStatus(
        "Unable to update password.",
        "error"
      );
    }
  }

  async function loadAccount() {

    const mount =
      document.getElementById("hire-ready-account");

    if (!mount) return;

    const token = getToken();

    if (!token) {
      window.location.href = "/login/";
      return;
    }

    mount.innerHTML = `
      <section class="hr-account-wrap">
        <div class="hr-account-hero">
          <h1>Loading Account...</h1>
        </div>
      </section>
    `;

    try {

      const response =
        await accountFetch("/api/auth/me");

      const user =
        await response.json();

      if (!response.ok) {
        throw new Error("Authentication required");
      }

      renderAccount(user);

    } catch (error) {

      console.error(error);

      mount.innerHTML = `
        <section class="hr-account-wrap">
          <div class="hr-account-status error">
            Unable to load account details.
          </div>
        </section>
      `;
    }
  }

  document.addEventListener(
    "DOMContentLoaded",
    loadAccount
  );

})();
