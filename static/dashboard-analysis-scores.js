console.log("Hire Ready dashboard-analysis-scores.js loaded");

(function () {
  const API_BASE = "https://resume-writer.onrender.com";

  function escapeScoreHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  async function scoreFetch(url) {
    if (typeof window.hireReadyFetch === "function") {
      return window.hireReadyFetch(url);
    }

    const token = localStorage.getItem("hire_ready_token");
    return fetch(url, {
      headers: {
        Authorization: "Bearer " + token
      }
    });
  }

  function getDocumentIdFromCard(card) {
    const button = card.querySelector("button[onclick*='viewResumeAnalysis']");
    if (!button) return "";

    const clickText = button.getAttribute("onclick") || "";
    const firstQuote = clickText.indexOf("'");
    const secondQuote = clickText.indexOf("'", firstQuote + 1);

    if (firstQuote === -1 || secondQuote === -1) return "";
    return clickText.substring(firstQuote + 1, secondQuote);
  }

  function renderScoreBox(analysis) {
    if (!analysis) {
      return `
        <div class="resume-latest-analysis" style="margin:12px 0;padding:12px;border:1px solid #e4e7ec;border-radius:10px;background:#f9fafb;color:#475467;">
          <strong style="display:block;color:#101828;margin-bottom:4px;">Latest Analysis</strong>
          <span>No saved analysis yet.</span>
        </div>
      `;
    }

    return `
      <div class="resume-latest-analysis" style="margin:12px 0;padding:12px;border:1px solid #d9eaff;border-radius:10px;background:#f5fbff;">
        <strong style="display:block;color:#101828;margin-bottom:8px;">Latest Analysis</strong>
        <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;">
          <span style="padding:6px 10px;border-radius:999px;background:#fff;border:1px solid #d0d5dd;color:#101828;font-weight:700;">
            Overall ${escapeScoreHtml(analysis.overall_score || 0)}
          </span>
          <span style="padding:6px 10px;border-radius:999px;background:#fff;border:1px solid #d0d5dd;color:#101828;font-weight:700;">
            ATS ${escapeScoreHtml(analysis.ats_score || 0)}
          </span>
        </div>
      </div>
    `;
  }

  async function addLatestScoresToResumeCards() {
    const cards = Array.from(document.querySelectorAll("#resume-list .resume-card"));
    if (!cards.length) return;

    try {
      const response = await scoreFetch(`${API_BASE}/api/resume-analysis/history`);
      const result = await response.json();

      if (!response.ok || !result.success) {
        console.warn("Could not load latest analysis scores", result);
        return;
      }

      const latestByDocumentId = new Map();

      (result.analyses || []).forEach((analysis) => {
        if (!analysis.document_id) return;

        const existing = latestByDocumentId.get(analysis.document_id);
        const currentTime = new Date(analysis.created_at || 0).getTime();
        const existingTime = existing ? new Date(existing.created_at || 0).getTime() : 0;

        if (!existing || currentTime >= existingTime) {
          latestByDocumentId.set(analysis.document_id, analysis);
        }
      });

      cards.forEach((card) => {
        const documentId = getDocumentIdFromCard(card);
        if (!documentId) return;

        const existingBox = card.querySelector(".resume-latest-analysis");
        if (existingBox) existingBox.remove();

        const updatedLine = Array.from(card.querySelectorAll("p"))
          .find((item) => item.textContent.includes("Updated:"));

        if (!updatedLine) return;

        const container = document.createElement("div");
        container.innerHTML = renderScoreBox(latestByDocumentId.get(documentId));
        updatedLine.insertAdjacentElement("afterend", container.firstElementChild);
      });
    } catch (error) {
      console.error("Latest analysis score display error:", error);
    }
  }

  function scheduleScoreEnhancement() {
    window.setTimeout(addLatestScoresToResumeCards, 800);
    window.setTimeout(addLatestScoresToResumeCards, 1800);
  }

  document.addEventListener("DOMContentLoaded", scheduleScoreEnhancement);

  const originalLoadMyResumes = window.loadMyResumes;
  if (typeof originalLoadMyResumes === "function") {
    window.loadMyResumes = async function enhancedLoadMyResumes() {
      const result = await originalLoadMyResumes.apply(this, arguments);
      scheduleScoreEnhancement();
      return result;
    };
  }
})();