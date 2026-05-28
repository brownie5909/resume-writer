import os
from dotenv import load_dotenv

load_dotenv()


# Security configuration functions
def get_allowed_origins():
    """Get allowed origins from environment variable with proper defaults"""
    origins_env = os.getenv("ALLOWED_ORIGINS", "")
    
    if origins_env:
        origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]
    else:
        # Default origins for development and production
        origins = [
            "http://localhost:3000",
            "http://localhost:8000", 
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "https://jobreadytools.com.au",
            "https://www.jobreadytools.com.au"
        ]
    
    print(f"🌐 CORS allowed origins: {origins}")
    return origins

def get_trusted_hosts():
    """Get trusted hosts from environment variable with proper defaults"""
    hosts_env = os.getenv("TRUSTED_HOSTS", "")
    
    if hosts_env:
        hosts = [host.strip() for host in hosts_env.split(",") if host.strip()]
    else:
        # Default hosts for development and production
        hosts = [
            "localhost", 
            "127.0.0.1", 
            "*.localhost",
            "resume-writer.onrender.com",
            "*.onrender.com",
            "jobreadytools.com.au",
            "www.jobreadytools.com.au",
            "*.jobreadytools.com.au"
        ]
    
    print(f"🔒 Trusted hosts: {hosts}")
    return hosts

# Validate SECRET_KEY for production
SECRET_KEY = os.getenv("SECRET_KEY", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    if not SECRET_KEY or SECRET_KEY == "hire-ready-super-secret-jwt-key-change-this-in-production-123456789":
        raise ValueError("❌ CRITICAL: You must set a secure SECRET_KEY for production!")
    print("✅ Production mode: SECRET_KEY is configured")
else:
    if not SECRET_KEY:
        print("⚠️  WARNING: Using default SECRET_KEY in development. Change for production!")
