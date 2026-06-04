console.log("Hire Ready dashboard-analysis-history.js loaded");

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

  function formatDate(value) {
    if (!value) return "";
    try {
      return new Date(value).toLocaleDateString("en-AU", {
        year: "numeric",
        month: "short",
        day: "numeric"
      });
    } catch (error) {
      return value;
    }
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

  function injectAnalysisSection() {
    const dashboard = document.getElementById("hire-ready-dashboard");
    const stats = document.querySelector(".dashboard-stats");
    const resumeList = document.getElementById("resume-list");

    if (!dashboard || !stats || !resumeList) {
      return false;
    }

    if (!document.getElementById("analysis-count")) {
      stats.insertAdjacentHTML("beforeend", `
        <div class="stat-card">
          <div class="stat-number" id="analysis-count">0</div>
          <div class="stat-label">Analyses</div>
        </div>
      `);
    }

    if (!document.getElementById("analysis-list")) {
      resumeList.insertAdjacentHTML("afterend", `
        <h2 style="margin-top: 34px;">My Analyses</h2>
        <p id="analysis-status">Loading your saved analyses...</p>
        <div id="analysis-list"></div>
      `);
    }

    loadMyAnalyses();
    return true;
  }

  async function loadMyAnalyses() {
    const token = getToken();
    const status = document.getElementById("analysis-status");
    const list = document.getElementById("analysis-list");
    const count = document.getElementById("analysis-count");

    if (!status || !list) {
      return;
    }

    if (!token) {
      status.innerHTML = "Please log in to view your saved analyses.";
      list.innerHTML = "";
      if (count) count.innerHTML = "0";
      return;
    }

    status.innerHTML = "Loading your saved analyses...";

    try {
      const response = await hireReadyFetch(`${API_BASE}/api/resume-analysis/history`);
      const result = await response.json();

      console.log("My Analyses Response:", result);

      if (!response.ok || !result.success) {
        status.innerHTML = result.detail || result.error || "Could not load analyses.";
        list.innerHTML = "";
        if (count) count.innerHTML = "0";
        return;
      }

      const analyses = Array.isArray(result.analyses) ? result.analyses : [];

      if (count) {
        count.innerHTML = analyses.length;
      }

      if (!analyses.length) {
        status.innerHTML = "You do not have any saved resume analyses yet.";
        list.innerHTML = `
          <div class="resume-card">
            <p>Run a resume analysis to start building your ATS score history.</p>
            <a href="/premium-resume-analysis/" class="resume-btn">Analyse Resume</a>
          </div>
        `;
        return;
      }

      status.innerHTML = "";
      list.innerHTML = analyses.map((analysis) => {
        const targetRole = analysis.target_role || "Not specified";
        const originalFile = analysis.original_filename || "Resume analysis";
        const overallScore = analysis.overall_score ?? "-";
        const atsScore = analysis.ats_score ?? "-";
        const analysedDate = formatDate(analysis.created_at);
        const documentId = analysis.document_id || "";

        return `
          <div class="resume-card">
            <h3>${escapeHtml(targetRole)}</h3>
            <p><strong>Original file:</strong> ${escapeHtml(originalFile)}</p>
            <p><strong>Overall Score:</strong> ${escapeHtml(overallScore)} &nbsp; <strong>ATS Score:</strong> ${escapeHtml(atsScore)}</p>
            <p><strong>Analysed:</strong> ${escapeHtml(analysedDate)}</p>
            <div class="resume-actions">
              <button class="resume-btn" onclick="window.viewResumeAnalysis ? viewResumeAnalysis('${escapeHtml(documentId)}', this) : alert('Analysis viewer is not available yet. Please refresh the page.');">View Analysis</button>
            </div>
          </div>
        `;
      }).join("");

    } catch (error) {
      console.error("Load analyses error:", error);
      status.innerHTML = "Error loading analyses. Please refresh the page.";
      if (count) count.innerHTML = "0";
    }
  }

  function startAnalysisHistoryInjection() {
    let attempts = 0;
    const maxAttempts = 30;

    const timer = window.setInterval(() => {
      attempts += 1;

      if (injectAnalysisSection() || attempts >= maxAttempts) {
        window.clearInterval(timer);
      }
    }, 300);
  }

  document.addEventListener("DOMContentLoaded", startAnalysisHistoryInjection);
  window.addEventListener("load", startAnalysisHistoryInjection);
})();
