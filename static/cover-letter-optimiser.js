console.log("Hire Ready cover-letter-optimiser.js loaded");

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

  function listHtml(items) {
    if (!Array.isArray(items) || !items.length) {
      return "<p>No items returned.</p>";
    }
    return `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
  }

  async function hireReadyFetch(url, options = {}) {
    const token = getToken();
    const firstOptions = {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: "Bearer " + token
      }
    };

    let response = await fetch(url, firstOptions);
    if (response.status !== 401) return response;

    const refreshToken = localStorage.getItem("hire_ready_refresh_token");
    if (!refreshToken) return response;

    const refreshResponse = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken })
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
        Authorization: "Bearer " + refreshData.access_token
      }
    });
  }

  function setStatus(message, type) {
    const status = document.getElementById("clo-status");
    if (!status) return;
    status.className = `clo-status ${type || ""}`;
    status.innerHTML = escapeHtml(message || "");
  }

  function setButtonLoading(isLoading) {
    const button = document.getElementById("clo-submit");
    if (!button) return;
    button.disabled = isLoading;
    button.innerHTML = isLoading ? "Optimising..." : "Optimise Cover Letter";
  }

  function renderResults(result) {
    const resultsBox = document.getElementById("clo-results");
    const analysis = result.analysis || {};

    if (!resultsBox) return;

    resultsBox.classList.add("active");
    resultsBox.innerHTML = `
      <div class="clo-card">
        <h2>Your Cover Letter Optimisation</h2>

        <div class="clo-score-grid">
          <div class="clo-score">
            <span>${escapeHtml(analysis.overall_score || 0)}</span>
            <small>Overall</small>
          </div>
          <div class="clo-score">
            <span>${escapeHtml(analysis.ats_score || 0)}</span>
            <small>ATS</small>
          </div>
          <div class="clo-score">
            <span>${escapeHtml(analysis.job_alignment_score || 0)}</span>
            <small>Role Match</small>
          </div>
        </div>

        <div class="clo-result-grid">
          <div class="clo-result-box">
            <h3>Strengths</h3>
            ${listHtml(analysis.strengths)}

            <h3>Improvements</h3>
            ${listHtml(analysis.specific_improvements)}
          </div>

          <div class="clo-result-box">
            <h3>Weaknesses</h3>
            ${listHtml(analysis.weaknesses)}

            <h3>Job Specific Tips</h3>
            ${listHtml(analysis.job_specific_tips)}
          </div>
        </div>

        <h3>Optimised Cover Letter</h3>
        <pre class="clo-output">${escapeHtml(result.improved_cover_letter || "")}</pre>
      </div>
    `;

    resultsBox.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function checkCanRun() {
    const token = getToken();
    if (!token) {
      setStatus("Please log in to use the Cover Letter Optimiser.", "error");
      return;
    }

    try {
      const response = await hireReadyFetch(`${API_BASE}/api/cover-letter-optimiser/can-run`);
      const data = await response.json();

      if (!response.ok || !data.success) return;

      if (!data.can_run) {
        setStatus(data.message || "Your monthly limit has been reached.", "error");
        const upgradeBox = document.getElementById("clo-upgrade");
        if (upgradeBox) {
          upgradeBox.innerHTML = `
            <div class="clo-upgrade">
              <strong>Upgrade to Premium</strong>
              <p>${escapeHtml(data.message || "Upgrade for unlimited cover letter optimisation.")}</p>
              <a href="/pricing/" class="clo-btn">View Pricing</a>
            </div>
          `;
        }
      }
    } catch (error) {
      console.warn("Could not check optimiser usage", error);
    }
  }

  async function optimiseCoverLetter(event) {
    event.preventDefault();

    const token = getToken();
    if (!token) {
      setStatus("Please log in to use the Cover Letter Optimiser.", "error");
      return;
    }

    const payload = {
      title: document.getElementById("clo-title")?.value || "Optimised Cover Letter",
      target_role: document.getElementById("clo-target-role")?.value || null,
      company_name: document.getElementById("clo-company")?.value || null,
      job_posting: document.getElementById("clo-job-posting")?.value || null,
      cover_letter_text: document.getElementById("clo-cover-letter")?.value || ""
    };

    if (payload.cover_letter_text.trim().length < 50) {
      setStatus("Please paste a complete cover letter before optimising.", "error");
      return;
    }

    setButtonLoading(true);
    setStatus("Optimising your cover letter...", "");

    try {
      const response = await hireReadyFetch(`${API_BASE}/api/cover-letter-optimiser/optimise`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        setStatus(result.error || result.detail || "Cover letter optimisation failed.", "error");
        if (result.upgrade_required) {
          const upgradeBox = document.getElementById("clo-upgrade");
          if (upgradeBox) {
            upgradeBox.innerHTML = `
              <div class="clo-upgrade">
                <strong>Upgrade to Premium</strong>
                <p>${escapeHtml(result.message || result.error || "Upgrade for unlimited optimisation.")}</p>
                <a href="/pricing/" class="clo-btn">View Pricing</a>
              </div>
            `;
          }
        }
        return;
      }

      setStatus("Cover letter optimised and saved successfully.", "success");
      renderResults(result);
    } catch (error) {
      console.error("Cover letter optimiser error:", error);
      setStatus("Something went wrong. Please try again.", "error");
    } finally {
      setButtonLoading(false);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("clo-form");
    if (form) {
      form.addEventListener("submit", optimiseCoverLetter);
      checkCanRun();
    }
  });
})();
