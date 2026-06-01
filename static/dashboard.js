console.log("Hire Ready dashboard.js loaded");

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

function setButtonLoading(button, isLoading, loadingText) {
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

async function loadMyResumes() {
  const token = getToken();
  const status = document.getElementById("resume-status");
  const list = document.getElementById("resume-list");

  if (!status || !list) {
    console.warn("Dashboard container missing resume-status or resume-list element.");
    return;
  }

  if (!token) {
    status.innerHTML = "Please log in to view your saved resumes.";
    list.innerHTML = "";
    return;
  }

  status.innerHTML = "Loading your saved resumes...";

  try {
    const response = await fetch(`${API_BASE}/api/resumes`, {
      headers: {
        Authorization: "Bearer " + token
      }
    });

    const result = await response.json();
    console.log("My Resumes Response:", result);

    if (!response.ok || !result.success) {
      status.innerHTML = result.detail || result.error || "Could not load resumes. Please log in again.";
      list.innerHTML = "";
      return;
    }

    if (!result.resumes || result.resumes.length === 0) {
      status.innerHTML = "You do not have any saved resumes yet.";
      list.innerHTML = "";
      return;
    }

    status.innerHTML = "";
    list.innerHTML = result.resumes.map(resume => `
      <div class="resume-card">
        <h3>${escapeHtml(resume.title || "Untitled Resume")}</h3>
        <p><strong>Template:</strong> ${escapeHtml(resume.template || "default")}</p>
        <p><strong>Updated:</strong> ${escapeHtml(formatDate(resume.updated_at || resume.created_at))}</p>

        <div class="resume-actions">
          <button class="resume-btn" onclick="viewResume('${resume.document_id}', this)">View</button>
          <button class="resume-btn" onclick="downloadResume('${resume.document_id}', this)">Download PDF</button>
          <button class="resume-btn" onclick="duplicateResume('${resume.document_id}', this)">Duplicate</button>
          <button class="resume-btn resume-btn-danger" onclick="deleteResume('${resume.document_id}', this)">Delete</button>
        </div>
      </div>
    `).join("");

  } catch (error) {
    console.error("Load resumes error:", error);
    status.innerHTML = "Error loading resumes. Please refresh the page.";
  }
}

async function viewResume(documentId, button) {
  setButtonLoading(button, true, "Opening...");

  try {
    const response = await fetch(`${API_BASE}/api/resumes/${documentId}`, {
      headers: {
        Authorization: "Bearer " + getToken()
      }
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
      alert("Could not load this resume.");
      return;
    }

    const resume = result.resume;
    const popup = window.open("", "_blank");

    if (!popup) {
      alert("Popup blocked. Please allow popups for this site.");
      return;
    }

    popup.document.write(`
      <html>
        <head>
          <title>${escapeHtml(resume.title)}</title>
          <style>
            body {
              font-family: Arial, sans-serif;
              padding: 30px;
              line-height: 1.6;
              max-width: 900px;
              margin: auto;
            }
            pre {
              white-space: pre-wrap;
              font-family: Arial, sans-serif;
            }
          </style>
        </head>
        <body>
          <h1>${escapeHtml(resume.title)}</h1>
          <pre>${escapeHtml(resume.resume_text || "")}</pre>
        </body>
      </html>
    `);
    popup.document.close();

  } catch (error) {
    console.error("View resume error:", error);
    alert("Something went wrong opening this resume.");
  } finally {
    setButtonLoading(button, false);
  }
}

async function downloadResume(documentId, button) {
  setButtonLoading(button, true, "Preparing PDF...");

  try {
    const response = await fetch(`${API_BASE}/api/resumes/${documentId}/pdf`, {
      method: "POST",
      headers: {
        Authorization: "Bearer " + getToken()
      }
    });

    if (!response.ok) {
      const error = await response.json();
      console.error(error);
      alert(error.detail?.error || "Could not download PDF.");
      return;
    }

    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = "resume.pdf";
    document.body.appendChild(link);
    link.click();

    link.remove();
    window.URL.revokeObjectURL(downloadUrl);

  } catch (error) {
    console.error("Download PDF error:", error);
    alert("Error downloading PDF.");
  } finally {
    setButtonLoading(button, false);
  }
}

async function duplicateResume(documentId, button) {
  setButtonLoading(button, true, "Duplicating...");

  try {
    const response = await fetch(`${API_BASE}/api/resumes/${documentId}/duplicate`, {
      method: "POST",
      headers: {
        Authorization: "Bearer " + getToken()
      }
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
      alert("Could not duplicate resume.");
      return;
    }

    await loadMyResumes();

  } catch (error) {
    console.error("Duplicate resume error:", error);
    alert("Error duplicating resume.");
  } finally {
    setButtonLoading(button, false);
  }
}

async function deleteResume(documentId, button) {
  const confirmed = confirm("Are you sure you want to delete this resume? This cannot be undone.");

  if (!confirmed) return;

  setButtonLoading(button, true, "Deleting...");

  try {
    const response = await fetch(`${API_BASE}/api/resumes/${documentId}`, {
      method: "DELETE",
      headers: {
        Authorization: "Bearer " + getToken()
      }
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
      alert("Could not delete resume.");
      return;
    }

    await loadMyResumes();

  } catch (error) {
    console.error("Delete resume error:", error);
    alert("Error deleting resume.");
  } finally {
    setButtonLoading(button, false);
  }
}

function initialiseHireReadyDashboard() {
  const dashboard = document.getElementById("hire-ready-dashboard");

  if (!dashboard) {
    console.warn("hire-ready-dashboard container not found.");
    return;
  }

  dashboard.innerHTML = `
    <section class="hire-ready-dashboard-wrap">
      <div class="dashboard-header">
        <h2>My Resumes</h2>
        <p>View, download, duplicate and manage your saved resumes.</p>
      </div>
      <p id="resume-status">Loading your saved resumes...</p>
      <div id="resume-list"></div>
    </section>
  `;

  loadMyResumes();
}

document.addEventListener("DOMContentLoaded", initialiseHireReadyDashboard);
