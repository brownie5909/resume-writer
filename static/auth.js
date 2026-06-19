console.log("Hire Ready auth.js loaded");

const HIRE_READY_API_BASE = "https://resume-writer.onrender.com";

function hireReadySaveAuth(data) {
  localStorage.setItem("hire_ready_token", data.access_token);
  localStorage.setItem("hire_ready_refresh_token", data.refresh_token);
  localStorage.setItem("hire_ready_user", JSON.stringify(data.user));
  localStorage.setItem("hire_ready_tier", data.user.tier);
}

function hireReadyGetToken() {
  return localStorage.getItem("hire_ready_token");
}

function hireReadySetStatus(message, type) {
  const status = document.getElementById("hire-ready-auth-status");
  if (!status) return;
  status.className = `hire-ready-auth-status ${type || ""}`;
  status.textContent = message || "";
}

function hireReadySetButtonLoading(button, isLoading, text) {
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

function hireReadyRedirectToDashboard() {
  window.location.href = "/dashboard/";
}

async function hireReadySubmitLogin(event) {
  event.preventDefault();
  const button = event.target.querySelector("button[type='submit']");
  const email = document.getElementById("hire-ready-login-email").value.trim();
  const password = document.getElementById("hire-ready-login-password").value;

  if (!email || !password) {
    hireReadySetStatus("Please enter your email and password.", "error");
    return;
  }

  hireReadySetButtonLoading(button, true, "Logging in...");
  hireReadySetStatus("Logging in...", "");

  try {
    const response = await fetch(`${HIRE_READY_API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();

    if (!response.ok) {
      hireReadySetStatus(data.detail || "Login failed. Please check your details.", "error");
      return;
    }

    hireReadySaveAuth(data);
    hireReadySetStatus("Login successful. Opening your dashboard...", "success");
    hireReadyRedirectToDashboard();
  } catch (error) {
    console.error("Login error:", error);
    hireReadySetStatus("Could not connect to the login service. Please try again.", "error");
  } finally {
    hireReadySetButtonLoading(button, false);
  }
}

async function hireReadySubmitRegister(event) {
  event.preventDefault();
  const button = event.target.querySelector("button[type='submit']");
  const fullName = document.getElementById("hire-ready-register-name").value.trim();
  const email = document.getElementById("hire-ready-register-email").value.trim();
  const password = document.getElementById("hire-ready-register-password").value;
  const confirmPassword = document.getElementById("hire-ready-register-confirm-password").value;
  const termsAgree = document.getElementById("hire-ready-terms-agree");

  if (!fullName || !email || !password || !confirmPassword) {
    hireReadySetStatus("Please complete all fields.", "error");
    return;
  }

  if (password !== confirmPassword) {
    hireReadySetStatus("Passwords do not match.", "error");
    return;
  }

  if (password.length < 8) {
    hireReadySetStatus("Password must be at least 8 characters.", "error");
    return;
  }

  if (!termsAgree || !termsAgree.checked) {
    hireReadySetStatus("Please agree to the Terms & Conditions and Privacy Policy before creating your account.", "error");
    return;
  }

  hireReadySetButtonLoading(button, true, "Creating account...");
  hireReadySetStatus("Creating your account...", "");

  try {
    const response = await fetch(`${HIRE_READY_API_BASE}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        full_name: fullName,
        email,
        password
      })
    });

    const data = await response.json();

    if (!response.ok) {
      const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
      hireReadySetStatus(detail || "Registration failed. Please try again.", "error");
      return;
    }

    hireReadySaveAuth(data);
    hireReadySetStatus("Account created. Opening your dashboard...", "success");
    hireReadyRedirectToDashboard();
  } catch (error) {
    console.error("Register error:", error);
    hireReadySetStatus("Could not connect to the registration service. Please try again.", "error");
  } finally {
    hireReadySetButtonLoading(button, false);
  }
}

function hireReadyRenderLogin(container) {
  container.innerHTML = `
    <div class="hire-ready-auth-wrap">
      <div class="hire-ready-auth-card">
        <h1>Login</h1>
        <p class="hire-ready-auth-intro">Access your saved resumes, cover letters, and dashboard.</p>
        <form id="hire-ready-login-form">
          <label class="hire-ready-auth-label" for="hire-ready-login-email">Email</label>
          <input id="hire-ready-login-email" class="hire-ready-auth-input" type="email" autocomplete="email" required>

          <label class="hire-ready-auth-label" for="hire-ready-login-password">Password</label>
          <input id="hire-ready-login-password" class="hire-ready-auth-input" type="password" autocomplete="current-password" required>

          <button class="hire-ready-auth-btn" type="submit">Login</button>
        </form>
        <p id="hire-ready-auth-status" class="hire-ready-auth-status"></p>
        <div class="hire-ready-auth-links">
          <p>No account yet? <a href="/register/">Create one here</a></p>
          <p><a href="/forgot-password/">Forgot password?</a></p>
        </div>
      </div>
    </div>
  `;

  document.getElementById("hire-ready-login-form").addEventListener("submit", hireReadySubmitLogin);
}

function hireReadyRenderRegister(container) {
  container.innerHTML = `
    <div class="hire-ready-auth-wrap">
      <div class="hire-ready-auth-card">
        <h1>Create Account</h1>
        <p class="hire-ready-auth-intro">Create your Hire Ready account to save resumes and access your dashboard.</p>
        <form id="hire-ready-register-form">
          <label class="hire-ready-auth-label" for="hire-ready-register-name">Full Name</label>
          <input id="hire-ready-register-name" class="hire-ready-auth-input" type="text" autocomplete="name" required>

          <label class="hire-ready-auth-label" for="hire-ready-register-email">Email</label>
          <input id="hire-ready-register-email" class="hire-ready-auth-input" type="email" autocomplete="email" required>

          <label class="hire-ready-auth-label" for="hire-ready-register-password">Password</label>
          <input id="hire-ready-register-password" class="hire-ready-auth-input" type="password" autocomplete="new-password" required>
          <p class="hire-ready-auth-small">Use at least 8 characters, including a letter and a number.</p>

          <label class="hire-ready-auth-label" for="hire-ready-register-confirm-password">Confirm Password</label>
          <input id="hire-ready-register-confirm-password" class="hire-ready-auth-input" type="password" autocomplete="new-password" required>

          <label class="hire-ready-auth-terms" for="hire-ready-terms-agree">
            <input id="hire-ready-terms-agree" type="checkbox" required>
            <span>
              I agree to the
              <a href="/terms-and-conditions/" target="_blank" rel="noopener">Terms & Conditions</a>
              and
              <a href="/privacy-policy/" target="_blank" rel="noopener">Privacy Policy</a>.
            </span>
          </label>

          <button class="hire-ready-auth-btn" type="submit">Create Account</button>
        </form>
        <p id="hire-ready-auth-status" class="hire-ready-auth-status"></p>
        <div class="hire-ready-auth-links">
          <p>Already have an account? <a href="/login/">Login here</a></p>
        </div>
      </div>
    </div>
  `;

  document.getElementById("hire-ready-register-form").addEventListener("submit", hireReadySubmitRegister);
}

function hireReadyInitAuthPage() {
  const loginContainer = document.getElementById("hire-ready-login");
  const registerContainer = document.getElementById("hire-ready-register");

  if (hireReadyGetToken() && (loginContainer || registerContainer)) {
    hireReadyRedirectToDashboard();
    return;
  }

  if (loginContainer) {
    hireReadyRenderLogin(loginContainer);
  }

  if (registerContainer) {
    hireReadyRenderRegister(registerContainer);
  }
}

document.addEventListener("DOMContentLoaded", hireReadyInitAuthPage);
