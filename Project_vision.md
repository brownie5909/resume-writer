Hire Ready AI Resume Platform
Architecture & Design Philosophy

Version: 1.0
Project Owner: Andrew Brown
Repository: brownie5909/resume-writer

Project Vision

Hire Ready is designed to provide practical AI-powered job application tools for Australian job seekers.

The objective is not to build another AI chatbot.

The objective is to build a professional suite of career tools that help people obtain employment through better resumes, cover letters and interview preparation.

Every feature should solve a real problem for the user while remaining simple to understand.

Core Design Philosophy

The platform follows several strict design principles.

1. Practical before Clever

Features should solve genuine employment problems.

Avoid AI features that exist purely because AI can generate them.

Every tool should improve a user's chances of obtaining employment.

2. Simplicity

Pages should be clean.

Avoid clutter.

One obvious action should exist on each page.

If a user needs instructions to use a feature, the design should probably be simplified.

3. Small Safe Changes

This project has evolved considerably.

Large rewrites are avoided.

Instead:

• inspect existing code

• make minimal changes

• preserve working functionality

• avoid regression

4. Preserve Existing Architecture

Do not rewrite working systems.

Instead improve them.

Especially avoid changing:

Authentication

Dashboard

Resume Storage

Stripe Integration

Database

These systems are considered production components.

Technology Stack

Frontend

WordPress EasyWP

Gutenberg

Minimal HTML blocks

Static JavaScript

Static CSS

Backend

FastAPI

Python

PostgreSQL

JWT Authentication

Render Hosting

Payments

Stripe Checkout

Stripe Customer Portal

Webhook Integration

AI

OpenAI

Resume generation

Resume analysis

Cover letters

Interview preparation

Frontend Philosophy

WordPress is only responsible for:

Pages

Menus

SEO

Content

Simple HTML containers

Business logic should remain inside:

static/*.js

Styling should remain inside:

static/*.css

Avoid embedding JavaScript into WordPress pages wherever possible.

Dashboard Philosophy

Dashboard is the user's workspace.

It should remain simple.

Sections include:

My Resumes

My Cover Letters

Interview Preparation

Plan & Usage

Account Settings

Avoid adding unnecessary sections.

Example:

"My Analyses" was intentionally removed because analysis belongs with each resume.

Resume Philosophy

The Resume Builder creates ATS-friendly resumes.

The Resume Analysis improves resumes.

The Resume Builder is not intended to produce graphic designer resumes.

Focus is:

ATS compatibility

Professional formatting

Australian employment market

Resume Analysis Philosophy

Analysis must always improve the resume.

Rules:

Analysis should never reduce quality.

Scores should remain the same or improve.

Recommendations should be automatically applied whenever possible.

Only recommendations requiring user knowledge should remain as suggestions.

Examples:

✔ Improve formatting

✔ Simplify wording

✔ Improve headings

✔ Standardise bullet points

✔ Improve ATS structure

Examples requiring user input:

Quantified achievements

Missing certifications

Additional employment history

Referees

These remain recommendations.

Resume Versioning

Every analysis creates a new version.

Original resume is preserved.

Improved resumes become:

Version 2

Version 3

Version 4

etc.

Users should never lose previous work.

Cover Letter Philosophy

Cover letters should:

match the resume

match the job advertisement

remain professional

avoid exaggerated AI language

Interview Preparation Philosophy

Interview preparation should help users prepare.

Not overwhelm them.

Information should be:

Company overview

Likely questions

Preparation tips

STAR examples

User Experience

Every page should answer:

What is this?

Why do I need it?

What should I do next?

Users should never wonder where to click.

Subscription Philosophy

Basic

Allow genuine use.

Show value.

Premium

Unlimited tools.

Professional features.

Do not artificially cripple the free version.

Instead encourage upgrading naturally.

Security Principles

Never expose:

API keys

Password hashes

Database credentials

Stripe secrets

Return friendly error messages.

Log technical errors server-side.

Coding Standards

Always inspect before changing.

Prefer extending existing code.

Avoid duplicate functions.

Avoid creating parallel systems.

Keep JavaScript modular.

Keep CSS page-specific unless styles are genuinely shared.

Database Philosophy

GitHub stores:

Application code

Migration scripts

Configuration

Documentation

PostgreSQL stores:

Users

Resumes

Cover letters

Interview preparation

Analysis history

Subscriptions

Never store production data in GitHub.

AI Development Rules

Future AI assistants working on this project should:

Inspect existing files first.

Understand existing architecture.

Avoid rewriting working systems.

Make small safe changes.

Maintain compatibility with WordPress.

Maintain compatibility with PostgreSQL.

Maintain compatibility with Stripe.

Avoid introducing unnecessary complexity.

Launch Status

Current platform includes:

✔ Authentication

✔ Password Reset

✔ Dashboard

✔ Resume Builder

✔ Resume Analysis

✔ Resume Versioning

✔ Cover Letter Generator

✔ Cover Letter Optimiser

✔ Interview Preparation

✔ Stripe Integration

✔ Customer Portal

✔ Admin Dashboard

✔ Support Page

✔ Privacy Policy

✔ Terms & Conditions

Long-Term Vision

Hire Ready should become Australia's most practical AI employment platform.

The emphasis is:

Quality

Reliability

Professional presentation

Ease of use

Practical outcomes

The platform should feel like professional employment software enhanced by AI, rather than an AI demonstration.
