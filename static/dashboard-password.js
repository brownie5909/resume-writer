console.log("Hire Ready dashboard-password.js loaded");

(function () {
  function updateDashboardAccountAction() {
    const actions = document.querySelector(".dashboard-actions");
    if (!actions) return;

    const existingForgotLink = document.querySelector('.dashboard-actions a[href="/forgot-password/"]');
    const existingAccountLink = document.querySelector('.dashboard-actions a[href="/account/"]');
    const legacyPasswordButton = document.getElementById("dashboard-change-password-btn");

    if (existingAccountLink) {
      existingAccountLink.textContent = "Account Settings";
      return;
    }

    if (existingForgotLink) {
      existingForgotLink.href = "/account/";
      existingForgotLink.textContent = "Account Settings";
      return;
    }

    if (legacyPasswordButton) {
      const accountLink = document.createElement("a");
      accountLink.href = "/account/";
      accountLink.className = "resume-btn";
      accountLink.textContent = "Account Settings";
      legacyPasswordButton.replaceWith(accountLink);
      return;
    }

    const accountLink = document.createElement("a");
    accountLink.href = "/account/";
    accountLink.className = "resume-btn";
    accountLink.textContent = "Account Settings";
    actions.appendChild(accountLink);
  }

  document.addEventListener("DOMContentLoaded", function () {
    window.setTimeout(updateDashboardAccountAction, 150);
  });
})();
