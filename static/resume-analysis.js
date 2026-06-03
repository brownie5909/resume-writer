console.log("Hire Ready resume-analysis.js loaded");

const HIRE_READY_ANALYSIS_API_BASE = "https://resume-writer.onrender.com";

function getHireReadyToken() {
  return localStorage.getItem("hire_ready_token");
}

function escapeAnalysisHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function setAnalysisButtonLoading(button, isLoading, loadingText) {
  if (!button) return;

  if (isLoading) {
    button.dataset.originalText = button.innerHTML;
    button.classList.add("loading");
    button.disabled = true;
    button.innerHTML = loadingText;
  } else {
    button.classList.remove("loading");
    button.disabled = false;
    button.innerHTML = button.dataset.originalText || button.innerHTML;
  }
}

async function hireReadyAnalysisFetch(url, options = {}) {
  const token = getHireReadyToken();

  const firstOptions = {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: "Bearer " + token
    }
  };

  let response = await fetch(url, firstOptions);

  if (response.status !== 401) {
    return response;
  }

  const refreshToken = localStorage.getItem("hire_ready_refresh_token");

  if (!refreshToken) {
    return response;
  }

  const refreshResponse = await fetch(`${HIRE_READY_ANALYSIS_API_BASE}/api/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      refresh_token: refreshToken
    })
  });

  if (!refreshResponse.ok) {
    localStorage.removeItem("hire_ready_token");
    localStorage.removeItem("hire_ready_refresh_token");
    localStorage.removeItem("hire_ready_user");
    localStorage.removeItem("hire_ready_tier");
    return response;
  }

  const refreshData = await refreshResponse.json();

  localStorage.setItem("hire_ready_token", refreshData.access_token);
  localStorage.setItem("hire_ready_refresh_token", refreshData.refresh_token);
  localStorage.setItem("hire_ready_user", JSON.stringify(refreshData.user));
  localStorage.setItem("hire_ready_tier", refreshData.user.tier);

  const retryOptions = {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: "Bearer " + refreshData.access_token
    }
  };

  return fetch(url, retryOptions);
}

function showAnalysisNotice(message, type = "info") {
  const notice = document.getElementById("analysis-notice");
  if (!notice) return;

  notice.className = `analysis-notice ${type}`;
  notice.innerHTML = message;
}

function renderList(items) {
  if (!Array.isArray(items) || !items.length) {
    return "<p>No items returned.</p>";
  }

  return `<ul>${items.map(item => `<li>${escapeAnalysisHtml(item)}</li>`).join("")}</ul>`;
}

function renderObjectAsList(value) {
  if (!value || typeof value !== "object") {
    return "<p>No details returned.</p>";
  }

  return `
    <ul>
      ${Object.entries(value).map(([key, item]) => `
        <li><strong>${escapeAnalysisHtml(key.replaceAll("_", " "))}:</strong> ${escapeAnalysisHtml(typeof item === "object" ? JSON.stringify(item) : item)}</li>
      `).join("")}
    </ul>
  `;
}

function renderAnalysisResults(result) {
  const output = document.getElementById("analysis-results");
  if (!output) return;

  const analysis = result.analysis || {};

  output.innerHTML = `
    <div class="analysis-results-card">
      <div class="analysis-score-grid">
        <div class="analysis-score-card">
          <span>${escapeAnalysisHtml(analysis.overall_score || 0)}</span>
          <small>Overall Score</small>
        </div>
        <div class="analysis-score-card">
          <span>${escapeAnalysisHtml(analysis.ats_score || 0)}</span>
          <small>ATS Score</small>
        </div>
        <div class="analysis-score-card">
          <span>${escapeAnalysisHtml(analysis.formatting_score || 0)}</span>
          <small>Formatting</small>
        </div>
      </div>

      <div class="analysis-saved-box">
        <strong>Saved to your dashboard:</strong>
        <p>${escapeAnalysisHtml(result.saved_resume?.title || "Analysed resume")}</p>
        <a class="analysis-btn analysis-btn-secondary" href="/dashboard/">Open Dashboard</a>
      </div>

      <h3>Strengths</h3>
      ${renderList(analysis.strengths)}

      <h3>Weaknesses</h3>
      ${renderList(analysis.weaknesses)}

      <h3>Specific Improvements</h3>
      ${renderList(analysis.specific_improvements)}

      <h3>ATS Recommendations</h3>
      ${renderList(analysis.ats_recommendations)}

      <h3>Keyword Analysis</h3>
      ${renderObjectAsList(analysis.keyword_analysis)}

      <h3>Section Analysis</h3>
      ${renderObjectAsList(analysis.sections_analysis)}

      <h3>Improved Resume</h3>
      <pre class="analysis-improved-resume">${escapeAnalysisHtml(result.improved_resume || "")}</pre>
    </div>
  `;
}

async function checkAnalysisAvailability() {
  const token = getHireReadyToken();

  if (!token) {
    showAnalysisNotice(
      "Please log in before using Resume Analysis. This tool is linked to your account so your improved resume can be saved to your dashboard.",
      "error"
    );
    return;
  }

  try {
    const response = await hireReadyAnalysisFetch(`${HIRE_READY_ANALYSIS_API_BASE}/api/resume-analysis/can-run`);
    const result = await response.json();

    if (!response.ok || !result.success) {
      showAnalysisNotice("Could not check your Resume Analysis allowance. Please log in again.", "error");
      return;
    }

    if (!result.can_run) {
      showAnalysisNotice(
        `${escapeAnalysisHtml(result.message)} <br><a href="/pricing/" class="analysis-inline-link">Upgrade to Premium</a>`,
        "warning"
      );
      return;
    }

    if (result.monthly_limit === 1) {
      showAnalysisNotice(
        `Basic includes 1 Resume Analysis per month. You have used ${escapeAnalysisHtml(result.current_usage)} of ${escapeAnalysisHtml(result.monthly_limit)} this month.`,
        "info"
      );
    } else {
      showAnalysisNotice("Resume Analysis is available on your account.", "success");
    }

  } catch (error) {
    console.error("Analysis allowance check error:", error);
    showAnalysisNotice("Could not check your Resume Analysis allowance. Please refresh and try again.", "error");
  }
}

async function analyzeResume(event) {
  event.preventDefault();

  const token = getHireReadyToken();
  const fileInput = document.getElementById("analysis-file");
  const targetRoleInput = document.getElementById("analysis-target-role");
  const button = document.getElementById("analysis-submit-btn");
  const output = document.getElementById("analysis-results");

  if (!token) {
    showAnalysisNotice("Please log in before using Resume Analysis.", "error");
    return;
  }

  if (!fileInput?.files?.length) {
    showAnalysisNotice("Please choose a resume file before starting analysis.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  if (targetRoleInput?.value?.trim()) {
    formData.append("target_role", targetRoleInput.value.trim());
  }

  setAnalysisButtonLoading(button, true, "Analysing...");
  showAnalysisNotice("Analysing your resume. Your improved version will be saved to your dashboard when complete.", "info");

  if (output) {
    output.innerHTML = "";
  }

  try {
    const response = await hireReadyAnalysisFetch(`${HIRE_READY_ANALYSIS_API_BASE}/api/analyze-resume`, {
      method: "POST",
      body: formData
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
      const message = result.error || result.detail?.error || result.detail || "Resume analysis failed.";
      showAnalysisNotice(
        result.upgrade_required
          ? `${escapeAnalysisHtml(message)} <br><a href="/pricing/" class="analysis-inline-link">Upgrade to Premium</a>`
          : escapeAnalysisHtml(message),
        result.upgrade_required ? "warning" : "error"
      );
      return;
    }

    showAnalysisNotice("Resume analysis complete. Your improved resume has been saved to your dashboard.", "success");
    renderAnalysisResults(result);
    await checkAnalysisAvailability();

  } catch (error) {
    console.error("Resume analysis error:", error);
    showAnalysisNotice("Something went wrong analysing your resume. Please try again.", "error");
  } finally {
    setAnalysisButtonLoading(button, false);
  }
}

function initialiseResumeAnalysisPage() {
  const root = document.getElementById("hire-ready-resume-analysis");

  if (!root) {
    console.warn("hire-ready-resume-analysis container not found.");
    return;
  }

  root.innerHTML = `
    <section class="analysis-wrap">
      <div class="analysis-hero">
        <p class="analysis-kicker">Hire Ready Premium Tool</p>
        <h1>Resume Optimiser & ATS Analysis</h1>
        <p>Upload your existing resume, receive an ATS-focused analysis, and save an improved editable version directly to your dashboard.</p>
      </div>

      <div id="analysis-notice" class="analysis-notice"></div>

      <form id="resume-analysis-form" class="analysis-form">
        <label for="analysis-file">Upload Resume</label>
        <input id="analysis-file" type="file" accept=".pdf,.doc,.docx,.txt,.rtf" required>
        <p class="analysis-help">Accepted files: PDF, DOC, DOCX, TXT, RTF. Maximum file size: 10MB.</p>

        <label for="analysis-target-role">Target Role</label>
        <input id="analysis-target-role" type="text" placeholder="Example: Property Manager, Administration Assistant, Apprentice Barber">
        <p class="analysis-help">Optional, but recommended. A target role improves ATS keyword feedback.</p>

        <button id="analysis-submit-btn" class="analysis-btn" type="submit">Analyse Resume</button>
      </form>

      <div id="analysis-results" class="analysis-results"></div>
    </section>
  `;

  document.getElementById("resume-analysis-form")?.addEventListener("submit", analyzeResume);
  checkAnalysisAvailability();
}

document.addEventListener("DOMContentLoaded", initialiseResumeAnalysisPage);
