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
  const savedTitle = result.saved_resume?.title || "Analysed resume";

  output.innerHTML = `
    <div class="analysis-results-card">
      <h2>Resume Analysis Complete</h2>
      <p class="analysis-help">
        Your analysis results and improved resume draft have been saved to your dashboard.
      </p>

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
        <p>${escapeAnalysisHtml(savedTitle)}</p>
        <p class="analysis-help">
          Open your dashboard to review saved versions, edit your resume, and download the PDF.
        </p>
        <a class="analysis-btn analysis-btn-secondary" href="/dashboard/">Open Dashboard</a>
      </div>

      <h3>Step 1: What We Found</h3>

      <h4>Strengths</h4>
      ${renderList(analysis.strengths)}

      <h4>Areas For Improvement</h4>
      ${renderList(analysis.weaknesses)}

      <h4>Specific Improvements</h4>
      ${renderList(analysis.specific_improvements)}

      <h4>ATS Recommendations</h4>
      ${renderList(analysis.ats_recommendations)}

      <h4>Keyword Analysis</h4>
      ${renderObjectAsList(analysis.keyword_analysis)}

      <h4>Section Analysis</h4>
      ${renderObjectAsList(analysis.sections_analysis)}

      <h3>Step 2: Improved Resume Draft</h3>
      <div class="analysis-saved-box">
        <strong>Review before using.</strong>
        <p>
          This improved version has been created using the recommendations from your analysis.
          Please review the content carefully and ensure all information remains accurate before using it in a job application.
        </p>
        <p>
          This improved resume has not yet been re-analysed. If you make further changes,
          run another analysis to review the updated version.
        </p>
      </div>

      <pre class="analysis-improved-resume">${escapeAnalysisHtml(result.improved_resume || "")}</pre>

      <h3>Step 3: Next Steps</h3>
      <div class="analysis-saved-box">
        <ul>
          <li>Review the improved resume draft for accuracy.</li>
          <li>Edit the saved resume from your dashboard if needed.</li>
          <li>Run another analysis after editing to check the updated version.</li>
          <li>Download your final PDF from the dashboard.</li>
        </ul>
        <a class="analysis-btn" href="/dashboard/">Open Dashboard</a>
      </div>
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

async function loadSavedResumesForAnalysis() {
  const select = document.getElementById("analysis-saved-resume");
  if (!select || !getHireReadyToken()) return;

  try {
    const response = await hireReadyAnalysisFetch(`${HIRE_READY_ANALYSIS_API_BASE}/api/resumes`);
    const result = await response.json();

    const resumes = Array.isArray(result)
      ? result
      : (result.resumes || result.documents || result.results || []);

    if (!Array.isArray(resumes) || !resumes.length) {
      return;
    }

    resumes.forEach(resume => {
      const option = document.createElement("option");
      option.value = resume.document_id;
      option.textContent = resume.title || "Saved Resume";
      select.appendChild(option);
    });
  } catch (error) {
    console.warn("Could not load saved resumes for analysis", error);
  }
}

function handleSavedResumeSelection() {
  const select = document.getElementById("analysis-saved-resume");
  const fileInput = document.getElementById("analysis-file");

  if (!select || !fileInput) return;

  if (select.value) {
    fileInput.required = false;
    fileInput.value = "";
    showAnalysisNotice("Saved resume selected. Click Analyse Resume to review this saved resume.", "info");
  } else {
    fileInput.required = true;
  }
}

async function analyzeResume(event) {
  event.preventDefault();

  const token = getHireReadyToken();
  const savedResumeSelect = document.getElementById("analysis-saved-resume");
  const fileInput = document.getElementById("analysis-file");
  const targetRoleInput = document.getElementById("analysis-target-role");
  const button = document.getElementById("analysis-submit-btn");
  const output = document.getElementById("analysis-results");

  if (!token) {
    showAnalysisNotice("Please log in before using Resume Analysis.", "error");
    return;
  }

  const savedResumeId = savedResumeSelect?.value || "";
  const hasUploadedFile = Boolean(fileInput?.files?.length);

  if (!savedResumeId && !hasUploadedFile) {
    showAnalysisNotice("Please choose a saved resume or upload a resume file before starting analysis.", "error");
    return;
  }

  setAnalysisButtonLoading(button, true, "Analysing...");
  showAnalysisNotice("Analysing your resume. Your results and improved resume draft will be saved to your dashboard when complete.", "info");

  if (output) {
    output.innerHTML = "";
  }

  try {
    let response;

    if (savedResumeId) {
      const formData = new FormData();
      if (targetRoleInput?.value?.trim()) {
        formData.append("target_role", targetRoleInput.value.trim());
      }

      response = await hireReadyAnalysisFetch(`${HIRE_READY_ANALYSIS_API_BASE}/api/resume-analysis/analyze-saved/${savedResumeId}`, {
        method: "POST",
        body: formData
      });
    } else {
      const formData = new FormData();
      formData.append("file", fileInput.files[0]);

      if (targetRoleInput?.value?.trim()) {
        formData.append("target_role", targetRoleInput.value.trim());
      }

      response = await hireReadyAnalysisFetch(`${HIRE_READY_ANALYSIS_API_BASE}/api/analyze-resume`, {
        method: "POST",
        body: formData
      });
    }

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

    showAnalysisNotice("Resume analysis complete. Review the improved resume draft below, then open your dashboard to edit or download.", "success");
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
        <p>Choose a saved resume or upload an existing file, receive an ATS-focused analysis, and review an improved resume draft saved to your dashboard.</p>
      </div>

      <div id="analysis-notice" class="analysis-notice"></div>

      <form id="resume-analysis-form" class="analysis-form">
        <label for="analysis-saved-resume">Choose Saved Resume</label>
        <select id="analysis-saved-resume">
          <option value="">Choose a saved resume, or upload a file below</option>
        </select>
        <p class="analysis-help">Select a resume already saved in your account, or leave this blank and upload a file.</p>

        <label for="analysis-file">Upload Resume</label>
        <input id="analysis-file" type="file" accept=".pdf,.doc,.docx,.txt,.rtf">
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
  document.getElementById("analysis-saved-resume")?.addEventListener("change", handleSavedResumeSelection);
  checkAnalysisAvailability();
  loadSavedResumesForAnalysis();
}

document.addEventListener("DOMContentLoaded", initialiseResumeAnalysisPage);
