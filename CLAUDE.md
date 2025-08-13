# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hire Ready is a FastAPI-based resume builder and job application platform with AI-powered features. The application provides user authentication, subscription management, resume generation, and analysis tools.

## Development Commands

### Environment Setup (REQUIRED)
Before running the application, set these critical environment variables:
```bash
# REQUIRED - Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'
export SECRET_KEY="your-secure-secret-key-here"

# Optional - defaults provided for development
export ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
export ALLOWED_HOSTS="localhost,127.0.0.1,*.hireready.com"
export PORT="8000"
```

### Running the Application
```bash
python main.py
```
The app runs on port 8000 by default (configurable via PORT environment variable).

**IMPORTANT**: The application will fail to start if SECRET_KEY is not set.

### Database Setup
```bash
python db_init.py
```
Initializes the SQLite database with all required tables.

### Dependencies
```bash
pip install -r requirements.txt
```

Note: Some features require additional dependencies (like `python-magic` for file validation) that may need OS-specific installation.

## Architecture Overview

### Core Structure
- **main.py**: FastAPI application entry point with main endpoints and PDF management
- **routes/**: Modular route handlers organized by feature
- **hire_ready.db**: SQLite database (created by db_init.py)

### Route Modules
- **user_management.py**: Authentication, user registration, JWT tokens, tier management
- **resume_analysis.py**: Resume upload and AI analysis features  
- **cover_letter.py**: Cover letter generation and analysis
- **interview.py**: Interview preparation and practice tools
- **admin.py**: Administrative functions and user management
- **subscriptions.py**: Stripe integration and subscription handling

### Key Features
- User authentication with JWT tokens and refresh tokens
- Three-tier subscription system (free, premium, professional)
- Usage tracking and limits per tier
- PDF generation and download with expiration
- SQLite database with comprehensive user and usage tracking

### Authentication System
- JWT-based authentication with refresh tokens
- Password hashing using bcrypt via passlib
- Email verification system
- Admin user privileges
- Feature access control based on user tiers

### Database Schema
Key tables include:
- `users`: User accounts and subscription info
- `usage_tracking`: Monthly feature usage per user
- `email_verification_tokens`: Email verification workflow
- `subscriptions`: Stripe subscription management
- Additional tables for admin logs and feature tracking

### Environment Configuration
- SECRET_KEY: JWT signing key
- PORT: Application port (default 8000)
- Stripe keys for subscription management
- Python 3.9.19 runtime specified

## Key Implementation Notes

### PDF Management
- In-memory PDF storage with 24-hour expiration
- User ownership verification for downloads
- Usage tracking only on actual download (not generation)
- Text-based mock PDFs for testing (not actual PDFs)

### Tier System
- Free: 1 PDF download/month, basic features
- Premium: Unlimited PDFs, AI analysis features  
- Professional: All features including advanced tools

## Security Implementation

### Critical Security Features (Recently Implemented)
- **Secure JWT Secret Management**: SECRET_KEY environment variable is required; application fails without it
- **Restricted CORS Policy**: Configurable allowed origins (no more wildcard *)
- **Database-Based Admin Authentication**: Admin access verified against database `is_admin` flag
- **SQL Injection Prevention**: Parameterized queries throughout admin routes
- **Comprehensive Input Validation**: Pydantic models with custom validators for all user inputs
- **File Upload Security**: Type, size, and MIME type validation for resume uploads
- **Trusted Host Middleware**: Protection against Host header attacks

### Authentication & Authorization
- JWT-based authentication with secure secret key management
- Password hashing using bcrypt via passlib
- Email verification system with time-based expiration
- Role-based access control with database verification
- Session management with refresh tokens
- User ownership verification for all document access

### Input Validation & Sanitization
- Pydantic models for all API endpoints with custom validators
- File upload restrictions (10MB max, specific MIME types only)
- Email validation with EmailStr type
- Name and text field sanitization with regex patterns
- Template choice validation against allowed values

### Environment Security
- Required SECRET_KEY environment variable (no hardcoded defaults)
- Configurable CORS origins for different deployment environments
- Trusted host middleware with configurable allowed hosts
- Environment-based configuration for all security settings

### Database Security
- Parameterized queries to prevent SQL injection
- Admin role verification against database (not email domains)
- Soft deletion patterns to maintain audit trails
- Usage tracking with proper user association

## Production Deployment Notes

### Required Environment Variables
```bash
SECRET_KEY=         # CRITICAL: Generate secure 32+ byte key
ALLOWED_ORIGINS=    # Comma-separated list of allowed frontend origins
ALLOWED_HOSTS=      # Comma-separated list of allowed host headers
```

### Security Checklist Before Deployment
- [ ] Set secure SECRET_KEY (never use defaults)
- [ ] Configure ALLOWED_ORIGINS for your domain only
- [ ] Set ALLOWED_HOSTS appropriately
- [ ] Review and test admin user creation process
- [ ] Verify file upload restrictions are working
- [ ] Test JWT token expiration and refresh
- [ ] Confirm database admin role assignment works correctly