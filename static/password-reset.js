console.log("Hire Ready password-reset.js loaded");

const HIRE_READY_PASSWORD_API_BASE = "https://resume-writer.onrender.com";

function hireReadyPasswordSetStatus(message, type) {
  const status = document.getElementById("hire-ready-auth-status");
  if (!status) return;
  status.className = `hire-ready-auth-status ${type || ""}`;
  status.innerHTML = message || "";
}

function hireReadyPasswordEscapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function hireReadyPasswordSetButtonLoading(button, isLoading, text) {
  if (!button) return;

  if (isLoading) {
    button.dataset.originalText = button.textContent;
    button.textContent = text;
    button.disabled = true;
    button.classList.add("loading");
  } else {
    button.textContent = button.dataset.originalText || button.textContent;
    button.disabled = false;
    button.classList.remove("loading");
  }
}

function hireReadyGetRecoveryTokenFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("token") || "";
}

async function hireReadySubmitForgotPassword(event) {
  event.preventDefault();

  const button = event.target.querySelector("button[type='submit']");
  const email = document.getElementById("hire-ready-forgot-email").value.trim();

  if (!email) {
    hireReadyPasswordSetStatus("Please enter your email address.", "error");
    return;
  }

  hireReadyPasswordSetButtonLoading(button, true, "Creating link...");
  hireReadyPasswordSetStatus("Creating password reset link...", "");

  try {
    const response = await fetch(`${HIRE_READY_PASSWORD_API_BASE}/api/auth/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });

    const data = await response.json();

    if (!response.ok) {
      hireReadyPasswordSetStatus(data.detail || "Could not create reset link.", "error");
      return;
    }

    if (data.reset_link) {
      hireReadyPasswordSetStatus(
        `Reset link created. For testing, open this link:<br><a href="${hireReadyPasswordEscapeHtml(data.reset_link)}">${hireReadyPasswordEscapeHtml(data.reset_link)}</a>`,
        "success"
      );
    } else {
      hireReadyPasswordSetStatus(data.message || "If an account exists, a reset link has been created.", "success");
    }
  } catch (error) {
    console.error("Forgot password error:", error);
    hireReadyPasswordSetStatus("Could not connect to the password reset service.", "error");
  } finally {
    hireReadyPasswordSetButtonLoading(button, false);
  }
}

async function hireReadySubmitResetPassword(event) {
  event.preventDefault();

  const button = event.target.querySelector("button[type='submit']");
  const token = hireReadyGetRecoveryTokenFromUrl();
  const newPassword = document.getElementById("hire-ready-reset-password").value;
  const confirmPassword = document.getElementById("hire-ready-reset-confirm-password").value;

  if (!token) {
    hireReadyPasswordSetStatus("This reset link is missing a token. Please request a new password reset link.", "error");
    return;
  }

  if (!newPassword || !confirmPassword) {
    hireReadyPasswordSetStatus("Please enter and confirm your new password.", "error");
    return;
  }

  if (newPassword !== confirmPassword) {
    hireReadyPasswordSetStatus("Passwords do not match.", "error");
    return;
  }

  if (newPassword.length < 8 || !/[A-Za-z]/.test(newPassword) || !/\d/.test(newPassword)) {
    hireReadyPasswordSetStatus("Password must be at least 8 characters and include a letter and a number.", "error");
    return;
  }

  hireReadyPasswordSetButtonLoading(button, true, "Updating password...");
  hireReadyPasswordSetStatus("Updating your password...", "");

  try {
    const response = await fetch(`${HIRE_READY_PASSWORD_API_BASE}/api/auth/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: newPassword })
    });

    const data = await response.json();

    if (!response.ok) {
      hireReadyPasswordSetStatus(data.detail || "Could not reset password.", "error");
      return;
    }

    localStorage.removeItem("hire_ready_token");
    localStorage.removeItem("hire_ready_refresh_token");
    localStorage.removeItem("hire_ready_user");
    localStorage.removeItem("hire_ready_tier");

    hireReadyPasswordSetStatus("Password updated. You can now login with your new password.", "success");
  } catch (error) {
    console.error("Reset password error:", error);
    hireReadyPasswordSetStatus("Could not connect to the password reset service.", "error");
  } finally {
    hireReadyPasswordSetButtonLoading(button, false);
  }
}

function hireReadyRenderForgotPassword(container) {
  container.innerHTML = `
    <div class="hire-ready-auth-wrap">
      <div class="hire-ready-auth-card">
        <h1>Forgot Password</h1>
        <p class="hire-ready-auth-intro">Enter your account email and we will create a password reset link.</p>
        <form id="hire-ready-forgot-form">
          <label class="hire-ready-auth-label" for="hire-ready-forgot-email">Email</label>
          <input id="hire-ready-forgot-email" class="hire-ready-auth-input" type="email" autocomplete="email" required>
          <button class="hire-ready-auth-btn" type="submit">Create Reset Link</button>
        </form>
        <p id="hire-ready-auth-status" class="hire-ready-auth-status"></p>
        <div class="hire-ready-auth-links">
          <p>Remembered your password? <a href="/login/">Login here</a></p>
        </div>
      </div>
    </div>
  `;

  document.getElementById("hire-ready-forgot-form").addEventListener("submit", hireReadySubmitForgotPassword);
}

function hireReadyRenderResetPassword(container) {
  const token = hireReadyGetRecoveryTokenFromUrl();

  container.innerHTML = `
    <div class="hire-ready-auth-wrap">
      <div class="hire-ready-auth-card">
        <h1>Reset Password</h1>
        <p class="hire-ready-auth-intro">Create a new password for your Hire Ready account.</p>
        <form id="hire-ready-reset-form">
          <label class="hire-ready-auth-label" for="hire-ready-reset-password">New Password</label>
          <input id="hire-ready-reset-password" class="hire-ready-auth-input" type="password" autocomplete="new-password" required>
          <p class="hire-ready-auth-small">Use at least 8 characters, including a letter and a number.</p>

          <label class="hire-ready-auth-label" for="hire-ready-reset-confirm-password">Confirm New Password</label>
          <input id="hire-ready-reset-confirm-password" class="hire-ready-auth-input" type="password" autocomplete="new-password" required>

          <button class="hire-ready-auth-btn" type="submit">Update Password</button>
        </form>
        <p id="hire-ready-auth-status" class="hire-ready-auth-status ${token ? "" : "error"}">${token ? "" : "This reset page was opened without a valid token."}</p>
        <div class="hire-ready-auth-links">
          <p><a href="/login/">Back to Login</a></p>
        </div>
      </div>
    </div>
  `;

  document.getElementById("hire-ready-reset-form").addEventListener("submit", hireReadySubmitResetPassword);
}

function hireReadyInitPasswordPages() {
  const forgotContainer = document.getElementById("hire-ready-forgot-password");
  const resetContainer = document.getElementById("hire-ready-reset-password-page");

  if (forgotContainer) {
    hireReadyRenderForgotPassword(forgotContainer);
  }

  if (resetContainer) {
    hireReadyRenderResetPassword(resetContainer);
  }
}

document.addEventListener("DOMContentLoaded", hireReadyInitPasswordPages);
