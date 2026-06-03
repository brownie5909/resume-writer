console.log("Hire Ready logout.js loaded");

const HIRE_READY_LOGOUT_API_BASE = "https://resume-writer.onrender.com";

function hireReadyClearAuthStorage() {
  localStorage.removeItem("hire_ready_token");
  localStorage.removeItem("hire_ready_refresh_token");
  localStorage.removeItem("hire_ready_user");
  localStorage.removeItem("hire_ready_tier");
}

async function hireReadyLogout() {
  const refreshToken = localStorage.getItem("hire_ready_refresh_token");

  try {
    if (refreshToken) {
      await fetch(`${HIRE_READY_LOGOUT_API_BASE}/api/auth/logout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          refresh_token: refreshToken
        })
      });
    }
  } catch (error) {
    console.warn("Logout API call failed, clearing browser session anyway.", error);
  }

  hireReadyClearAuthStorage();
  window.location.href = "/login/";
}

function hireReadyAddLogoutButton() {
  const actions = document.querySelector(".dashboard-actions");

  if (!actions || document.getElementById("hire-ready-logout-btn")) {
    return;
  }

  const button = document.createElement("button");
  button.id = "hire-ready-logout-btn";
  button.className = "resume-btn resume-btn-secondary";
  button.type = "button";
  button.textContent = "Logout";
  button.addEventListener("click", hireReadyLogout);

  actions.appendChild(button);
}

function hireReadyWaitForDashboardActions() {
  hireReadyAddLogoutButton();

  const interval = window.setInterval(() => {
    hireReadyAddLogoutButton();

    if (document.getElementById("hire-ready-logout-btn")) {
      window.clearInterval(interval);
    }
  }, 300);

  window.setTimeout(() => window.clearInterval(interval), 6000);
}

document.addEventListener("DOMContentLoaded", hireReadyWaitForDashboardActions);
