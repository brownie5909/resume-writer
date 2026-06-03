console.log("Hire Ready dashboard.js loaded");

const API_BASE = "https://resume-writer.onrender.com";
const ALLOWED_RESUME_TEMPLATES = ["default", "conservative", "creative", "executive"];

let currentEditingDocumentId = null;
let editOriginalSnapshot = "";
let editHasUnsavedChanges = false;
let currentVersionHistoryDocumentId = null;

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

function showDashboardNotice(message, type = "success") {
  const notice = document.getElementById("dashboard-notice");
  if (!notice) return;

  notice.className = `dashboard-notice ${type}`;
  notice.innerHTML = escapeHtml(message);

  window.setTimeout(() => {
    notice.innerHTML = "";
    notice.className = "dashboard-notice";
  }, 4500);
}

function getEditFormValues() {
  const selectedTemplate = document.getElementById("edit-template")?.value || "default";

  return {
    title: document.getElementById("edit-title")?.value.trim() || "",
    template: ALLOWED_RESUME_TEMPLATES.includes(selectedTemplate) ? selectedTemplate : "default",
    resume_text: document.getElementById("edit-resume-text")?.value || "",
    cover_letter_text: document.getElementById("edit-cover-letter-text")?.value || ""
  };
}

function serializeEditValues(values) {
  return JSON.stringify(values || getEditFormValues());
}

function updateEditDirtyState() {
  editHasUnsavedChanges = currentEditingDocumentId !== null && serializeEditValues() !== editOriginalSnapshot;
}

function startEditChangeTracking() {
  ["edit-title", "edit-template", "edit-resume-text", "edit-cover-letter-text"].forEach((fieldId) => {
    const field = document.getElementById(fieldId);
    if (!field) return;
    field.oninput = updateEditDirtyState;
    field.onchange = updateEditDirtyState;
  });
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
    const response = await hireReadyFetch(`${API_BASE}/api/resumes`);
    const result = await response.json();

    console.log("My Resumes Response:", result);

    if (!response.ok || !result.success) {
      status.innerHTML = result.detail || result.error || "Could not load resumes. Please log in again.";
      list.innerHTML = "";
      return;
    }

    const resumeCountElement = document.getElementById("resume-count");

    if (resumeCountElement) {
      resumeCountElement.innerHTML = result.resumes.length;
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
          <button class="resume-btn" onclick="editResume('${resume.document_id}', this)">Edit</button>
          <button class="resume-btn" onclick="openVersionHistory('${resume.document_id}', this)">Version History</button>
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
    const response = await hireReadyFetch(`${API_BASE}/api/resumes/${documentId}`);
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

async function editResume(documentId, button) {
  setButtonLoading(button, true, "Loading...");

  try {
    const response = await hireReadyFetch(`${API_BASE}/api/resumes/${documentId}`);
    const result = await response.json();

    if (!response.ok || !result.success) {
      alert("Could not load this resume for editing.");
      return;
    }

    const resume = result.resume;
    currentEditingDocumentId = documentId;

    const safeTemplate = ALLOWED_RESUME_TEMPLATES.includes(resume.template) ? resume.template : "default";

    document.getElementById("edit-title").value = resume.title || "";
    document.getElementById("edit-template").value = safeTemplate;
    document.getElementById("edit-resume-text").value = resume.resume_text || "";
    document.getElementById("edit-cover-letter-text").value = resume.cover_letter_text || "";
    document.getElementById("edit-modal-status").innerHTML = "";
    document.getElementById("edit-modal-status").className = "edit-modal-status";

    editOriginalSnapshot = serializeEditValues();
    editHasUnsavedChanges = false;

    openEditModal();
    startEditChangeTracking();

  } catch (error) {
    console.error("Edit resume error:", error);
    alert("Something went wrong loading this resume.");
  } finally {
    setButtonLoading(button, false);
  }
}

function openEditModal() {
  const modal = document.getElementById("resume-edit-modal");
  if (modal) {
    modal.classList.add("active");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("resume-modal-open");
  }
}

function closeEditModal(forceClose = false) {
  updateEditDirtyState();

  if (!forceClose && editHasUnsavedChanges) {
    const confirmed = confirm("You have unsaved changes. Close without saving?");
    if (!confirmed) return;
  }

  const modal = document.getElementById("resume-edit-modal");
  if (modal) {
    modal.classList.remove("active");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("resume-modal-open");
  }

  currentEditingDocumentId = null;
  editOriginalSnapshot = "";
  editHasUnsavedChanges = false;
}

async function saveEditedResume(button) {
  if (!currentEditingDocumentId) {
    alert("No resume is currently selected for editing.");
    return;
  }

  const status = document.getElementById("edit-modal-status");
  const editValues = getEditFormValues();

  if (!editValues.title) {
    status.className = "edit-modal-status error";
    status.innerHTML = "Please enter a resume title.";
    return;
  }

  setButtonLoading(button, true, "Saving...");
  status.className = "edit-modal-status";
  status.innerHTML = "Saving changes...";

  try {
    const response = await hireReadyFetch(`${API_BASE}/api/resumes/${currentEditingDocumentId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(editValues)
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
      console.error("Save resume error:", result);
      status.className = "edit-modal-status error";
      status.innerHTML = result.detail || result.error || "Could not save resume changes.";
      return;
    }

    editOriginalSnapshot = serializeEditValues(editValues);
    editHasUnsavedChanges = false;

    status.className = "edit-modal-status success";
    status.innerHTML = "Saved successfully.";
    showDashboardNotice("Resume saved successfully.", "success");

    closeEditModal(true);
    await loadMyResumes();

  } catch (error) {
    console.error("Save edited resume error:", error);
    status.className = "edit-modal-status error";
    status.innerHTML = "Error saving resume changes.";
  } finally {
    setButtonLoading(button, false);
  }
}

async function openVersionHistory(documentId, button) {
  currentVersionHistoryDocumentId = documentId;
  const modal = document.getElementById("resume-version-modal");
  const list = document.getElementById("version-history-list");
  const preview = document.getElementById("version-preview");
  const status = document.getElementById("version-modal-status");

  setButtonLoading(button, true, "Loading...");

  if (list) list.innerHTML = "Loading version history...";
  if (preview) preview.innerHTML = "Select a version to preview it.";
  if (status) {
    status.innerHTML = "";
    status.className = "edit-modal-status";
  }

  try {
    const response = await hireReadyFetch(`${API_BASE}/api/resumes/${documentId}/versions`);
    const result = await response.json();

    if (!response.ok || !result.success) {
      alert("Could not load version history.");
      return;
    }

    if (modal) {
      modal.classList.add("active");
      modal.setAttribute("aria-hidden", "false");
      document.body.classList.add("resume-modal-open");
    }

    const versions = result.versions || [];
    const versionLimit = result.version_limit;

    if (status && versionLimit === 1) {
      status.className = "edit-modal-status";
      status.innerHTML = "Basic includes 1 backup version. Upgrade to Premium for full version history.";
    }

    if (!versions.length) {
      list.innerHTML = `
        <div class="version-empty">
          No previous versions yet. A backup version is created when this resume is edited or replaced.
        </div>
      `;
      return;
    }

    list.innerHTML = versions.map(version => `
      <div class="version-history-item">
        <div>
          <strong>${escapeHtml(version.title || "Previous version")}</strong>
          <p>Saved ${escapeHtml(formatDate(version.created_at))}</p>
          <p>Template: ${escapeHtml(version.template || "default")}</p>
        </div>
        <div class="version-history-actions">
          <button class="resume-btn resume-btn-secondary" onclick="previewResumeVersion('${documentId}', '${version.version_id}', this)">Preview</button>
          <button class="resume-btn" onclick="restoreResumeVersion('${documentId}', '${version.version_id}', this)">Restore</button>
        </div>
      </div>
    `).join("");

  } catch (error) {
    console.error("Version history error:", error);
    alert("Something went wrong loading version history.");
  } finally {
    setButtonLoading(button, false);
  }
}

function closeVersionHistoryModal() {
  const modal = document.getElementById("resume-version-modal");
  if (modal) {
    modal.classList.remove("active");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("resume-modal-open");
  }
  currentVersionHistoryDocumentId = null;
}

async function previewResumeVersion(documentId, versionId, button) {
  const preview = document.getElementById("version-preview");
  setButtonLoading(button, true, "Opening...");

  try {
    const response = await hireReadyFetch(`${API_BASE}/api/resumes/${documentId}/versions/${versionId}`);
    const result = await response.json();

    if (!response.ok || !result.success) {
      alert("Could not preview this version.");
      return;
    }

    const version = result.version;
    preview.innerHTML = `
      <h3>${escapeHtml(version.title || "Previous version")}</h3>
      <p><strong>Saved:</strong> ${escapeHtml(formatDate(version.created_at))}</p>
      <p><strong>Template:</strong> ${escapeHtml(version.template || "default")}</p>
      <h4>Resume Text</h4>
      <pre>${escapeHtml(version.resume_text || "")}</pre>
      ${version.cover_letter_text ? `<h4>Cover Letter</h4><pre>${escapeHtml(version.cover_letter_text)}</pre>` : ""}
    `;

  } catch (error) {
    console.error("Preview version error:", error);
    alert("Something went wrong previewing this version.");
  } finally {
    setButtonLoading(button, false);
  }
}

async function restoreResumeVersion(documentId, versionId, button) {
  const confirmed = confirm("Restore this previous version? Your current resume will be saved as a backup before restoring.");
  if (!confirmed) return;

  const status = document.getElementById("version-modal-status");
  setButtonLoading(button, true, "Restoring...");

  if (status) {
    status.className = "edit-modal-status";
    status.innerHTML = "Restoring version...";
  }

  try {
    const response = await hireReadyFetch(`${API_BASE}/api/resumes/${documentId}/versions/${versionId}/restore`, {
      method: "POST"
    });
    const result = await response.json();

    if (!response.ok || !result.success) {
      console.error("Restore version error:", result);
      if (status) {
        status.className = "edit-modal-status error";
        status.innerHTML = result.detail || result.error || "Could not restore this version.";
      }
      return;
    }

    if (status) {
      status.className = "edit-modal-status success";
      status.innerHTML = "Version restored successfully.";
    }

    showDashboardNotice("Resume version restored successfully.", "success");
    closeVersionHistoryModal();
    await loadMyResumes();

  } catch (error) {
    console.error("Restore version error:", error);
    if (status) {
      status.className = "edit-modal-status error";
      status.innerHTML = "Error restoring version.";
    }
  } finally {
    setButtonLoading(button, false);
  }
}

async function downloadResume(documentId, button) {
  setButtonLoading(button, true, "Preparing PDF...");

  try {
    const response = await hireReadyFetch(`${API_BASE}/api/resumes/${documentId}/pdf`, {
      method: "POST"
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
    const response = await hireReadyFetch(`${API_BASE}/api/resumes/${documentId}/duplicate`, {
      method: "POST"
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
      alert(result.detail?.error || result.error || "Could not duplicate resume.");
      return;
    }

    showDashboardNotice("Resume duplicated successfully.", "success");
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
    const response = await hireReadyFetch(`${API_BASE}/api/resumes/${documentId}`, {
      method: "DELETE"
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
      alert("Could not delete resume.");
      return;
    }

    showDashboardNotice("Resume deleted successfully.", "success");
    await loadMyResumes();

  } catch (error) {
    console.error("Delete resume error:", error);
    alert("Error deleting resume.");
  } finally {
    setButtonLoading(button, false);
  }
}

async function loadDashboardUser() {
  try {
    const response = await hireReadyFetch(`${API_BASE}/api/auth/me`);
    const user = await response.json();

    if (!response.ok || !user.user_id) {
      console.warn("Could not load dashboard user", user);
      return;
    }

    document.getElementById("dashboard-name").innerHTML = `Welcome ${escapeHtml(user.full_name)}`;
    document.getElementById("dashboard-tier").innerHTML = `${escapeHtml(user.tier.toUpperCase())} PLAN`;

  } catch (error) {
    console.error("Load dashboard user error:", error);
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
        <h1 id="dashboard-name">Welcome</h1>
        <p id="dashboard-tier">Loading account...</p>
      </div>

      <div id="dashboard-notice" class="dashboard-notice"></div>

      <div class="dashboard-stats">
        <div class="stat-card">
          <div class="stat-number" id="resume-count">0</div>
          <div class="stat-label">Resumes</div>
        </div>
      </div>

      <div class="dashboard-actions">
        <a href="/create-resume/" class="resume-btn">Create Resume</a>
        <a href="/premium-resume-analysis/" class="resume-btn">Resume Analysis</a>
      </div>

      <h2>My Resumes</h2>
      <p id="resume-status">Loading your saved resumes...</p>
      <div id="resume-list"></div>

      <div id="resume-edit-modal" class="resume-edit-modal" aria-hidden="true">
        <div class="resume-edit-modal-backdrop" onclick="closeEditModal()"></div>
        <div class="resume-edit-modal-panel" role="dialog" aria-modal="true" aria-label="Edit resume">
          <div class="resume-edit-modal-header">
            <h2>Edit Resume</h2>
            <button class="resume-modal-close" onclick="closeEditModal()" aria-label="Close edit modal">×</button>
          </div>

          <label class="resume-edit-label" for="edit-title">Resume Title</label>
          <input id="edit-title" class="resume-edit-input" type="text">

          <label class="resume-edit-label" for="edit-template">Template</label>
          <select id="edit-template" class="resume-edit-input">
            <option value="default">Default</option>
            <option value="conservative">Conservative</option>
            <option value="creative">Creative</option>
            <option value="executive">Executive</option>
          </select>
          <p class="resume-edit-help">Changing the template affects the next PDF you download from this saved resume.</p>

          <label class="resume-edit-label" for="edit-resume-text">Resume Text</label>
          <textarea id="edit-resume-text" class="resume-edit-textarea" rows="16"></textarea>

          <label class="resume-edit-label" for="edit-cover-letter-text">Cover Letter Text</label>
          <textarea id="edit-cover-letter-text" class="resume-edit-textarea" rows="10"></textarea>

          <p id="edit-modal-status" class="edit-modal-status"></p>

          <div class="resume-edit-modal-actions">
            <button class="resume-btn" onclick="saveEditedResume(this)">Save Changes</button>
            <button class="resume-btn resume-btn-secondary" onclick="closeEditModal()">Cancel</button>
          </div>
        </div>
      </div>

      <div id="resume-version-modal" class="resume-edit-modal" aria-hidden="true">
        <div class="resume-edit-modal-backdrop" onclick="closeVersionHistoryModal()"></div>
        <div class="resume-edit-modal-panel" role="dialog" aria-modal="true" aria-label="Resume version history">
          <div class="resume-edit-modal-header">
            <h2>Version History</h2>
            <button class="resume-modal-close" onclick="closeVersionHistoryModal()" aria-label="Close version history modal">×</button>
          </div>

          <p id="version-modal-status" class="edit-modal-status"></p>

          <div class="version-history-layout">
            <div>
              <h3>Saved Versions</h3>
              <div id="version-history-list" class="version-history-list">Loading version history...</div>
            </div>
            <div>
              <h3>Preview</h3>
              <div id="version-preview" class="version-preview">Select a version to preview it.</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  `;

  loadDashboardUser();
  loadMyResumes();
}

window.addEventListener("beforeunload", function (event) {
  updateEditDirtyState();

  if (!editHasUnsavedChanges) return;

  event.preventDefault();
  event.returnValue = "";
});

document.addEventListener("DOMContentLoaded", initialiseHireReadyDashboard);
