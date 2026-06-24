# CLAUDE.md

This file guides Claude Code when working in the `brownie5909/resume-writer` repository.

## Project Overview

Hire Ready is a FastAPI backend for AI-assisted job application tools. It supports account management, subscriptions, resume generation, saved resume documents, resume analysis, cover letter tools, interview preparation, admin management, usage limits, and PDF downloads.

The current backend is not just a single-file API. `main.py` wires the app together, while reusable logic lives under `app/core`, `app/database`, `app/services`, `app/utils`, and feature routers in `routes`.

## Development Commands

### Install Dependencies

```bash
pip install -r requirements.txt
```

Some file parsing features depend on `python-magic`, which may require OS-level setup outside Python.

### Required Environment

`app/core/security.py` requires `SECRET_KEY` at import time. The API will fail to start without it.

```bash
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
export SECRET_KEY="your-secure-secret-key"
export OPENAI_API_KEY="your-openai-api-key"
```

Optional environment variables used by the current code:

```bash
export ENVIRONMENT="development"
export DATABASE_URL=""              # If set, app/database/db.py uses Postgres instead of SQLite
export ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
export TRUSTED_HOSTS="localhost,127.0.0.1,*.localhost"
export ACCESS_TOKEN_EXPIRE_MINUTES="30"
export REFRESH_TOKEN_EXPIRE_DAYS="7"
export DEMO_PREMIUM="false"
```

Admin bootstrap variables:

```bash
export AUTO_CREATE_ADMIN="true"
export ADMIN_EMAIL="admin@example.com"
export ADMIN_PASSWORD="StrongPassword123"
export ADMIN_FULL_NAME="Admin User"
```

### Run The API

Use an ASGI server; `main.py` defines `app` but does not contain a local `uvicorn.run(...)` block.

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Health checks:

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
```

### Database Setup

There are two database setup paths:

```bash
python db_init.py
```

`db_init.py` creates the legacy/core SQLite tables and optional local test users.

Current application code also uses `app.database.db.init_database()`, which supports SQLite by default and Postgres when `DATABASE_URL` is set. It creates newer tables such as `resume_documents`, `resume_versions`, `resume_analysis_results`, `cover_letter_optimiser_results`, `cover_letter_generator_results`, and `interview_preparation_results`.

For admin creation, prefer:

```bash
ADMIN_EMAIL="you@example.com" ADMIN_PASSWORD="StrongPassword123" python scripts/create_admin.py
```

## Architecture

### Entry Point

- `main.py` creates the FastAPI app, configures middleware, mounts `/static`, runs optional admin bootstrap, includes routers under `/api`, and owns the top-level resume generation and PDF download endpoints.
- App metadata currently reports `Hire Ready API` version `2.2.4`.

### Core Modules

- `app/core/config.py`: Loads `.env`, resolves CORS origins and trusted hosts, and validates production `SECRET_KEY` policy.
- `app/core/security.py`: Requires `SECRET_KEY`, defines JWT settings, password hashing, access token creation, and refresh token creation.
- `app/core/middleware.py`: Adds `TrustedHostMiddleware` and CORS middleware using config helpers.

### Database Layer

- `app/database/db.py` is the current database abstraction.
- It uses SQLite (`hire_ready.db`) unless `DATABASE_URL` is set, then it uses Postgres via `psycopg2` with SSL.
- `DatabaseCursor` converts `?` placeholders to `%s` for Postgres and handles a small subset of SQLite datetime expressions.
- SQLite rows are exposed as dict-like `RowDict` objects so code can use both key and index access.
- Keep SQL parameterized. Only interpolate table names from explicit allowlists, as done in `routes/resume_documents.py`.

### Service Layer

- `app/services/resume_generator.py`: Calls OpenAI `gpt-4.1-mini` and requires JSON output containing `resume_text`, `cover_letter`, and `ats_notes`. It is intentionally truth-preserving and ATS-focused for Australian job seekers.
- `app/services/pdf_service.py`: Generates real PDF bytes with ReportLab. The old guidance saying PDFs are mock text is no longer accurate.
- `app/services/resume_document_service.py`: Creates, lists, updates, duplicates, deletes, versions, and prunes saved resume documents.
- `app/services/admin_setup.py`: Optionally creates an admin user from environment variables when `AUTO_CREATE_ADMIN=true`.
- Additional services handle resume analysis, cover letter generation/optimisation, sessions, and interview preparation.

### Routers

All routers are mounted in `main.py` with the `/api` prefix.

- `routes/user_management.py`: Registration, login, JWT auth, refresh tokens, sessions, tier lookup, and user helpers.
- `routes/account_recovery.py`: Password/account recovery flows.
- `routes/account_settings.py`: Account settings management.
- `routes/admin.py`: Admin-only user and stats endpoints, guarded by the database `is_admin` flag.
- `routes/subscriptions.py`: Stripe subscription flows.
- `routes/billing_portal.py`: Stripe billing portal support.
- `routes/resume_documents.py`: Dashboard usage, saved resumes, resume versions, duplicate/delete/download flows, and plan-limit checks.
- `routes/resume_analysis.py`: File upload or saved-resume analysis, AI feedback, improved resume creation, history, and monthly usage enforcement.
- `routes/cover_letter.py`: Cover letter analysis/generation helpers from the earlier feature set.
- `routes/cover_letter_generator.py`: Saved cover letter generation workflow.
- `routes/cover_letter_optimiser.py`: Saved cover letter optimisation workflow.
- `routes/interview.py`: Interview practice tooling.
- `routes/interview_preparation.py`: Saved interview preparation workflow.

## Resume Generation Flow

Guest endpoint:

- `POST /api/generate-resume-guest`
- Runs AI generation and returns resume text, optional cover letter, and ATS notes.
- Does not create a PDF URL.
- Returns `requires_login_for_pdf: true`.

Authenticated endpoint:

- `POST /api/generate-resume`
- Requires `get_current_user`.
- Runs AI generation through `generate_resume_with_ai`.
- Generates PDF bytes through `generate_resume_pdf`.
- Saves or updates a resume document.
- Stores PDF bytes in the process-local `pdf_store` for up to 24 hours.
- Returns `/api/download-resume/{pdf_id}`.

Important save behavior:

- Basic/free users are limited to one saved resume and one version.
- Premium/professional users and admins have unlimited saved resumes and versions.
- If a basic/free user already has a saved resume, new generation overwrites the existing document and may snapshot a previous version.

## PDF Download Logic

- PDFs are generated with ReportLab and stored in memory, not permanently persisted as files.
- `pdf_store` entries expire after 24 hours when cleanup runs.
- Downloads require authentication and ownership checks.
- Usage is tracked only on first successful download for a generated `pdf_id`.
- Re-downloading the same `pdf_id` does not increment usage again.
- Guest PDF download attempts are rejected with a login-required response.

## Tier And Usage Rules

`routes/user_management.py` defines `UserTier` values:

- `basic`
- `free` legacy-compatible tier
- `premium`
- `professional`

Current PDF limits:

- Basic/free: 3 PDF downloads per month.
- Premium/professional: unlimited PDF downloads.

Dashboard usage in `routes/resume_documents.py` also reports monthly usage for resume analysis, cover letter generator, cover letter optimiser, interview preparation, and PDF downloads.

Admin users bypass saved-resume/version limits.

## Resume Analysis Logic

`routes/resume_analysis.py` accepts uploaded files or saved resume text.

Validation rules:

- Max upload size is 10MB.
- Allowed extensions: `.pdf`, `.doc`, `.docx`, `.txt`, `.rtf`.
- Allowed MIME types include PDF, Word, octet-stream, plain text, and RTF.
- Extracted text must contain enough content to analyze.

Analysis results are saved to `resume_analysis_results`, improved resumes are saved as resume documents, basic users are pruned to the latest allowed result, and monthly usage is incremented after a successful analysis.

## Security Notes

- Never add fallback hardcoded production secrets.
- `SECRET_KEY` is mandatory through `app/core/security.py`.
- Production validation in `app/core/config.py` rejects missing or known-default secrets when `ENVIRONMENT=production`.
- Auth uses JWT access and refresh tokens plus persisted session records.
- Passwords are hashed with bcrypt through passlib.
- Admin access must be checked with the `users.is_admin` database flag.
- Keep CORS and trusted host configuration environment-driven.
- Keep upload validation strict for extension, MIME type, and size.
- Keep user ownership checks on all saved document, analysis, version, and PDF download routes.

## Implementation Guidance

- Prefer adding business logic in `app/services/*` and keeping routers thin.
- Use `app.database.db.get_db()` for database work instead of opening raw SQLite connections in new code.
- Keep SQL compatible with both SQLite and Postgres where practical.
- Use parameterized queries. If a dynamic table name is unavoidable, guard it with an explicit allowlist.
- Preserve the stable API response shapes used by the frontend: most feature endpoints return `success`, saved entity IDs, usage status, and user-facing limit/upgrade details.
- When changing tier behavior, update both `TIER_LIMITS` and dashboard usage/limit helpers.
- When changing resume persistence, update both `main.py` generation behavior and `routes/resume_documents.py` document/version behavior.
- When changing AI prompts, preserve JSON-only output and do not allow the model to invent candidate facts.

## Deployment Checklist

- Set `SECRET_KEY` to a secure generated value.
- Set `OPENAI_API_KEY` for AI features.
- Set `ENVIRONMENT=production` in production.
- Set `DATABASE_URL` for Postgres deployments; leave unset for local SQLite.
- Configure `ALLOWED_ORIGINS` for the production frontend domains.
- Configure `TRUSTED_HOSTS` for deployed API hostnames.
- Configure Stripe environment variables used by subscription and billing portal routes.
- Create or repair an admin account with `scripts/create_admin.py` or controlled `AUTO_CREATE_ADMIN=true` bootstrap.
- Verify `/health` after deployment.
- Test login, refresh, PDF download limits, saved resume ownership, admin-only access, and upload validation.
