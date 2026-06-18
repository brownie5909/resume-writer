console.log("Hire Ready create-resume.js loaded");

(function () {
  const API_BASE = "https://resume-writer.onrender.com";

  function isAuthenticated() {
    return Boolean(window.HireReady && window.HireReady.API && window.HireReady.API.isAuthenticated());
  }

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

  function renderPage() {
    const mount = document.getElementById("hire-ready-create-resume");
    if (!mount) return;

    mount.innerHTML = `
      <section class="hr-resume-hero">
        <div class="hr-resume-hero-badge">Resume Builder</div>
        <h1>Create A Strong, ATS-Friendly Resume</h1>
        <p>
          Build a clear professional resume using your own experience, skills and career details.
          Your resume is generated as a clean single-column format with standard headings for ATS readability.
        </p>
      </section>

      <div id="auth-status" class="hr-resume-auth">
        Loading authentication status...
      </div>

      <div class="hr-resume-layout">
        <main class="hr-resume-card">
          <form id="resume-form" class="hr-resume-form">
            <section class="hr-resume-section">
              <h3>Personal Information</h3>
              <p class="hr-resume-section-note">Enter the details that should appear at the top of your resume.</p>
              <div class="hr-field-grid">
                <div class="hr-field">
                  <label for="full_name">Full Name *</label>
                  <input id="full_name" type="text" name="full_name" required placeholder="John Smith">
                </div>
                <div class="hr-field">
                  <label for="email">Email *</label>
                  <input id="email" type="email" name="email" required placeholder="john@example.com">
                </div>
                <div class="hr-field">
                  <label for="phone">Phone</label>
                  <input id="phone" type="tel" name="phone" placeholder="0400 000 000">
                </div>
                <div class="hr-field">
                  <label for="job_title">Target Job Title *</label>
                  <input id="job_title" type="text" name="job_title" required placeholder="Administration Officer">
                </div>
              </div>
            </section>

            <section class="hr-resume-section">
              <h3>Professional Summary</h3>
              <p class="hr-resume-section-note">Add a short overview of your background. Rough notes are fine.</p>
              <div class="hr-field-grid">
                <div class="hr-field full">
                  <label for="summary">Summary</label>
                  <textarea id="summary" name="summary" rows="4" placeholder="Briefly describe your experience, strengths and career focus..."></textarea>
                </div>
              </div>
            </section>

            <section class="hr-resume-section">
              <h3>Work Experience</h3>
              <p class="hr-resume-section-note">Add your most relevant recent role. You can include dot points or rough notes.</p>
              <div class="hr-field-grid">
                <div class="hr-field">
                  <label for="company">Company</label>
                  <input id="company" type="text" name="company" placeholder="ABC Company">
                </div>
                <div class="hr-field">
                  <label for="years_worked">Years Worked</label>
                  <input id="years_worked" type="text" name="years_worked" placeholder="2021 - Present">
                </div>
                <div class="hr-field full">
                  <label for="responsibilities">Responsibilities & Achievements</label>
                  <textarea id="responsibilities" name="responsibilities" rows="5" placeholder="Example: Managed customer enquiries, maintained records, prepared reports, supported team administration..."></textarea>
                </div>
              </div>
            </section>

            <section class="hr-resume-section">
              <h3>Education</h3>
              <div class="hr-field-grid">
                <div class="hr-field">
                  <label for="degree">Degree / Qualification</label>
                  <input id="degree" type="text" name="degree" placeholder="Certificate III in Business">
                </div>
                <div class="hr-field">
                  <label for="school">School / Provider</label>
                  <input id="school" type="text" name="school" placeholder="TAFE Queensland">
                </div>
              </div>
            </section>

            <section class="hr-resume-section">
              <h3>Skills</h3>
              <p class="hr-resume-section-note">List skills that are relevant to the job you are applying for.</p>
              <div class="hr-field-grid">
                <div class="hr-field full">
                  <label for="skills">Key Skills</label>
                  <textarea id="skills" name="skills" rows="4" placeholder="Customer service, data entry, communication, Microsoft Office, scheduling, attention to detail..."></textarea>
                </div>
              </div>
            </section>

            <section class="hr-resume-section">
              <h3>Options</h3>
              <div class="hr-field-grid">
                <div class="hr-field">
                  <label for="template_choice">Resume Style</label>
                  <select id="template_choice" name="template_choice">
                    <option value="default">Modern</option>
                    <option value="conservative">Conservative</option>
                    <option value="creative">Creative</option>
                    <option value="executive">Executive</option>
                  </select>
                </div>
                <div class="hr-field">
                  <label for="generate_cover_letter">Cover Letter</label>
                  <select id="generate_cover_letter" name="generate_cover_letter">
                    <option value="false">Resume only</option>
                    <option value="true">Generate resume and cover letter</option>
                  </select>
                </div>
              </div>
            </section>

            <div class="hr-resume-actions">
              <button type="submit" id="submit-btn" class="hr-resume-btn">
                Generate My Resume
              </button>
              <a href="/dashboard/" class="hr-resume-btn secondary">View Dashboard</a>
            </div>
          </form>
        </main>

        <aside class="hr-resume-side-card">
          <h3>ATS-Friendly By Default</h3>
          <p>
            Your resume is generated with a clean structure, standard headings and plain text sections.
          </p>
          <ul>
            <li>Single-column layout</li>
            <li>Standard resume headings</li>
            <li>No graphics or tables</li>
            <li>Clear bullet points</li>
            <li>Professional Australian wording</li>
          </ul>
        </aside>
      </div>

      <div id="results-container" class="hr-resume-results"></div>
    `;

    setupFormSubmission();
    window.setTimeout(updateAuthStatus, 1200);
  }

  async function updateAuthStatus() {
    const authStatus = document.getElementById("auth-status");
    if (!authStatus) return;

    if (isAuthenticated()) {
      authStatus.className = "hr-resume-auth success";
      authStatus.innerHTML = `
        <strong>Signed in.</strong> Your resume will be saved to your account.
        <a href="/dashboard/">View Dashboard</a>
      `;

      try {
        const userInfo = await window.HireReady.API.getCurrentUser();
        const nameField = document.querySelector('[name="full_name"]');
        const emailField = document.querySelector('[name="email"]');

        if (nameField && userInfo.full_name) nameField.value = userInfo.full_name;
        if (emailField && userInfo.email) emailField.value = userInfo.email;
      } catch (error) {
        console.warn("Could not pre-fill user data", error);
      }
    } else {
      authStatus.className = "hr-resume-auth warning";
      authStatus.innerHTML = `
        <strong>Sign in to save your work.</strong>
        <a href="/login?redirect=/create-resume/">Sign In</a>
      `;
    }
  }

  function setupFormSubmission() {
    const form = document.getElementById("resume-form");
    const submitBtn = document.getElementById("submit-btn");
    if (!form || !submitBtn) return;

    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      submitBtn.disabled = true;
      submitBtn.textContent = "Checking your plan...";
      form.classList.add("loading");

      try {
        const formData = new FormData(form);
        const data = {};

        for (const [key, value] of formData.entries()) {
          if (key === "generate_cover_letter") {
            data[key] = value === "true";
          } else {
            data[key] = value;
          }
        }

        const requestData = {
          data,
          template_choice: data.template_choice || "default",
          generate_cover_letter: Boolean(data.generate_cover_letter)
        };

        let response;

        if (isAuthenticated()) {
          const overwriteDecision = await checkBasicOverwriteBeforeGenerate();
          if (overwriteDecision === "cancel") return;

          submitBtn.textContent = overwriteDecision === "replace"
            ? "Replacing Saved Resume..."
            : "Generating Resume...";

          response = await window.HireReady.API.generateResume(requestData);
        } else {
          submitBtn.textContent = "Generating Resume...";

          const apiResponse = await fetch(`${API_BASE}/api/generate-resume-guest`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestData)
          });
          response = await apiResponse.json();
        }

        if (response.success) {
          showResults(response);
        } else {
          throw new Error(response.error || "Resume generation failed");
        }
      } catch (error) {
        showError(error.message);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Generate My Resume";
        form.classList.remove("loading");
      }
    });
  }

  async function checkBasicOverwriteBeforeGenerate() {
    try {
      const token = getToken();
      if (!token) return "create";

      const apiResponse = await fetch(`${API_BASE}/api/resumes/can-create`, {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!apiResponse.ok) return "create";

      const planCheck = await apiResponse.json();
      if (planCheck.can_create === false && planCheck.current_tier === "basic") {
        const userChoice = await showBasicOverwriteModal(planCheck);
        return userChoice ? "replace" : "cancel";
      }

      return "create";
    } catch (error) {
      console.warn("Resume limit check failed", error);
      return "create";
    }
  }

  function showBasicOverwriteModal(planCheck) {
    return new Promise((resolve) => {
      const existingModal = document.getElementById("basic-overwrite-modal");
      if (existingModal) existingModal.remove();

      const modal = document.createElement("div");
      modal.id = "basic-overwrite-modal";
      modal.className = "hr-overwrite-modal";
      modal.innerHTML = `
        <div class="hr-overwrite-box">
          <h3>Basic Plan Notice</h3>
          <p>Your Basic plan includes ${escapeHtml(planCheck.saved_resume_limit || 1)} saved resume.</p>

          <div class="hr-overwrite-warning">
            <strong>Generating a new resume will replace your current saved resume.</strong>
            <p>Your previous resume will be kept as a backup version so you can restore it later from Version History.</p>
          </div>

          <div class="hr-overwrite-upgrade">
            <strong>Upgrade to Premium to unlock:</strong>
            <ul>
              <li>Unlimited saved resumes</li>
              <li>Full version history</li>
              <li>ATS Analysis History</li>
              <li>Cover Letter Library</li>
            </ul>
          </div>

          <div class="hr-resume-actions">
            <a href="/pricing/" class="hr-resume-btn success">Upgrade to Premium</a>
            <button id="continue-replace-resume" type="button" class="hr-resume-btn">Continue & Replace</button>
            <button id="cancel-replace-resume" type="button" class="hr-resume-btn secondary">Cancel</button>
          </div>
        </div>
      `;

      document.body.appendChild(modal);

      document.getElementById("continue-replace-resume").addEventListener("click", function () {
        modal.remove();
        resolve(true);
      });

      document.getElementById("cancel-replace-resume").addEventListener("click", function () {
        modal.remove();
        resolve(false);
      });

      modal.addEventListener("click", function (event) {
        if (event.target === modal) {
          modal.remove();
          resolve(false);
        }
      });
    });
  }

  function showResults(response) {
    const resultsContainer = document.getElementById("results-container");
    if (!resultsContainer) return;

    const authenticated = isAuthenticated();
    const saveMessage = authenticated
      ? response.save_action === "updated_existing"
        ? "Your existing saved resume was replaced and the previous version was kept as a backup. You can download the PDF from your dashboard."
        : "Your resume has been saved to your dashboard. You can download the PDF from there."
      : "Your resume preview is ready. Sign in to save resumes and download PDFs.";

    resultsContainer.innerHTML = `
      <div class="hr-resume-results-card">
        <div class="hr-resume-results-header">
          <div>
            <h2>Resume Generated Successfully</h2>
            <p>${escapeHtml(saveMessage)}</p>
          </div>
        </div>

        <div class="hr-resume-preview">${escapeHtml(response.resume_text || "Resume generated successfully.")}</div>

        ${response.ats_notes ? `
          <div class="hr-resume-ats-note">
            <strong>ATS note:</strong> ${escapeHtml(response.ats_notes)}
          </div>
        ` : ""}

        <div class="hr-resume-actions" style="margin-top: 18px;">
          ${authenticated ? `<a href="/dashboard/" class="hr-resume-btn success">View Dashboard & Download PDF</a>` : `<a href="/login/" class="hr-resume-btn success">Sign In To Save</a>`}
          <button type="button" class="hr-resume-btn secondary" id="generate-another-btn">Generate Another</button>
        </div>
      </div>
    `;

    resultsContainer.classList.add("active");
    document.getElementById("generate-another-btn")?.addEventListener("click", generateAnother);
    resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function showError(message) {
    const resultsContainer = document.getElementById("results-container");
    if (!resultsContainer) return;

    resultsContainer.innerHTML = `
      <div class="hr-resume-error">
        <strong>Error</strong>
        <p>${escapeHtml(message)}</p>
      </div>
    `;
    resultsContainer.classList.add("active");
    resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function generateAnother() {
    const resultsContainer = document.getElementById("results-container");
    if (resultsContainer) {
      resultsContainer.classList.remove("active");
      resultsContainer.innerHTML = "";
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  document.addEventListener("DOMContentLoaded", renderPage);
})();
