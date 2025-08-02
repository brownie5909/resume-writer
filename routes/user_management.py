from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any
import os
import uuid
import secrets
import sqlite3
from contextlib import contextmanager
import hashlib
import re

router = APIRouter()
security = HTTPBearer(auto_error=False)

# Security setup
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserTier(Enum):
    FREE = "free"
    PREMIUM = "premium" 
    PROFESSIONAL = "professional"

# Your existing tier limits (keeping unchanged)
TIER_LIMITS = {
    UserTier.FREE: {
        "pdf_downloads_per_month": 1,
        "features": ["resume_builder", "company_research"],
        "description": "Basic resume builder + Company research"
    },
    UserTier.PREMIUM: {
        "pdf_downloads_per_month": -1,  # Unlimited
        "features": [
            "resume_builder", "company_research", "resume_analysis", 
            "cover_letter_analysis", "linkedin_optimization", "interview_practice",
            "ats_scoring", "job_customization"
        ],
        "description": "$19/month - AI Analysis + Cover Letters + Interview Prep"
    },
    UserTier.PROFESSIONAL: {
        "pdf_downloads_per_month": -1,  # Unlimited
        "features": [
            "resume_builder", "company_research", "resume_analysis", 
            "cover_letter_analysis", "linkedin_optimization", "interview_practice",
            "ats_scoring", "job_customization", "mock_interview_simulator", 
            "career_path_analysis", "salary_benchmarking", "skills_gap_analysis"
        ],
        "description": "$39/month - Everything + AI Mock Interviews + Career Analysis"
    }
}

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters long')
        return v.strip()

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    tier: str
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserResponse

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str

class EmailVerificationRequest(BaseModel):
    email: EmailStr

# Database setup and management
DB_PATH = "hire_ready.db"

def init_database():
    """Initialize SQLite database with required tables"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                tier TEXT DEFAULT 'free',
                is_verified BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT
            )
        """)
        
        # Email verification tokens
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_verification_tokens (
                token_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Password reset tokens
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # User sessions for tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                refresh_token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Usage tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_tracking (
                usage_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0,
                month_year TEXT NOT NULL,
                last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                UNIQUE(user_id, feature_name, month_year)
            )
        """)
        
        conn.commit()

@contextmanager
def get_db():
    """Database connection context manager"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    try:
        yield conn
    finally:
        conn.close()

# Security utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_verification_token() -> str:
    """Create secure verification token"""
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    """Hash a token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()

# Database operations
def create_user_db(user_data: UserCreate) -> str:
    """Create new user in database"""
    user_id = str(uuid.uuid4())
    password_hash = get_password_hash(user_data.password)
    
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (user_id, email, password_hash, full_name, tier)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, user_data.email.lower(), password_hash, user_data.full_name, UserTier.FREE.value))
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND is_active = TRUE", (email.lower(),))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Get user by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ? AND is_active = TRUE", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_user_login_time(user_id: str):
    """Update user's last login time"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET last_login = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = ?
        """, (user_id,))
        conn.commit()

def store_refresh_token(user_id: str, refresh_token: str) -> str:
    """Store refresh token in database"""
    session_id = str(uuid.uuid4())
    token_hash = hash_token(refresh_token)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_sessions (session_id, user_id, refresh_token_hash, expires_at)
            VALUES (?, ?, ?, ?)
        """, (session_id, user_id, token_hash, expires_at))
        conn.commit()
        return session_id

def verify_refresh_token(refresh_token: str) -> Optional[str]:
    """Verify refresh token and return user_id"""
    token_hash = hash_token(refresh_token)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id FROM user_sessions 
            WHERE refresh_token_hash = ? AND expires_at > CURRENT_TIMESTAMP AND is_active = TRUE
        """, (token_hash,))
        row = cursor.fetchone()
        return row[0] if row else None

def create_email_verification_token(user_id: str) -> str:
    """Create email verification token"""
    token = create_verification_token()
    token_hash = hash_token(token)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO email_verification_tokens (token_id, user_id, token_hash, expires_at)
            VALUES (?, ?, ?, ?)
        """, (str(uuid.uuid4()), user_id, token_hash, expires_at))
        conn.commit()
        
    return token

def verify_email_token(token: str) -> Optional[str]:
    """Verify email verification token"""
    token_hash = hash_token(token)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id FROM email_verification_tokens 
            WHERE token_hash = ? AND expires_at > CURRENT_TIMESTAMP AND used = FALSE
        """, (token_hash,))
        row = cursor.fetchone()
        
        if row:
            user_id = row[0]
            # Mark token as used and verify user
            cursor.execute("""
                UPDATE email_verification_tokens SET used = TRUE WHERE token_hash = ?
            """, (token_hash,))
            cursor.execute("""
                UPDATE users SET is_verified = TRUE, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?
            """, (user_id,))
            conn.commit()
            return user_id
    
    return None

# Enhanced user tier management (building on your existing functions)
def get_user_tier_enhanced(user_id: Optional[str] = None) -> UserTier:
    """Enhanced user tier lookup with database integration"""
    if not user_id:
        return UserTier.FREE
    
    # Check for testing accounts (keep your existing logic)
    if user_id == "premium_user":
        return UserTier.PREMIUM
    elif user_id == "pro_user":
        return UserTier.PROFESSIONAL
    elif os.getenv("DEMO_PREMIUM") == "true":
        return UserTier.PREMIUM
    
    # Database lookup
    user = get_user_by_id(user_id)
    if user:
        try:
            return UserTier(user['tier'])
        except ValueError:
            return UserTier.FREE
    
    return UserTier.FREE

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

# API Routes
@router.post("/auth/register", response_model=TokenResponse)
async def register_user(user_data: UserCreate):
    """Register a new user"""
    try:
        # Create user
        user_id = create_user_db(user_data)
        
        # Generate tokens
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_id}, expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(data={"sub": user_id})
        
        # Store refresh token
        store_refresh_token(user_id, refresh_token)
        
        # Get user data for response
        user = get_user_by_id(user_id)
        
        # Create verification token (for future email verification)
        verification_token = create_email_verification_token(user_id)
        
        # TODO: Send verification email here
        print(f"Verification token for {user_data.email}: {verification_token}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse(
                user_id=user["user_id"],
                email=user["email"],
                full_name=user["full_name"],
                tier=user["tier"],
                is_verified=user["is_verified"],
                created_at=datetime.fromisoformat(user["created_at"]),
                last_login=datetime.fromisoformat(user["last_login"]) if user["last_login"] else None
            )
        )
        
    except Exception as e:
        if "Email already registered" in str(e):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/auth/login", response_model=TokenResponse)
async def login_user(user_credentials: UserLogin):
    """Authenticate user and return tokens"""
    # Get user
    user = get_user_by_email(user_credentials.email)
    if not user or not verify_password(user_credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update login time
    update_user_login_time(user["user_id"])
    
    # Generate tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["user_id"]}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user["user_id"]})
    
    # Store refresh token
    store_refresh_token(user["user_id"], refresh_token)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            full_name=user["full_name"],
            tier=user["tier"],
            is_verified=user["is_verified"],
            created_at=datetime.fromisoformat(user["created_at"]),
            last_login=datetime.fromisoformat(user["last_login"]) if user["last_login"] else None
        )
    )

@router.post("/auth/refresh")
async def refresh_access_token(refresh_token: str):
    """Refresh access token using refresh token"""
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Verify refresh token in database
        stored_user_id = verify_refresh_token(refresh_token)
        if not stored_user_id or stored_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Generate new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_id}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        user_id=current_user["user_id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        tier=current_user["tier"],
        is_verified=current_user["is_verified"],
        created_at=datetime.fromisoformat(current_user["created_at"]),
        last_login=datetime.fromisoformat(current_user["last_login"]) if current_user["last_login"] else None
    )

@router.post("/auth/verify-email")
async def verify_email(token: str):
    """Verify user email with token"""
    user_id = verify_email_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    return {"message": "Email verified successfully"}

@router.post("/auth/resend-verification")
async def resend_verification_email(request: EmailVerificationRequest):
    """Resend email verification"""
    user = get_user_by_email(request.email)
    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, a verification link has been sent"}
    
    if user["is_verified"]:
        return {"message": "Email is already verified"}
    
    verification_token = create_email_verification_token(user["user_id"])
    
    # TODO: Send verification email here
    print(f"Verification token for {request.email}: {verification_token}")
    
    return {"message": "Verification email sent"}

# Enhanced existing endpoints with authentication
@router.get("/user/tier")
async def get_user_tier_info(current_user: dict = Depends(get_current_user)):
    """Get current user tier and feature access (now requires authentication)"""
    user_tier = get_user_tier_enhanced(current_user["user_id"])
    
    return {
        "current_tier": user_tier.value,
        "description": TIER_LIMITS[user_tier]["description"],
        "features": TIER_LIMITS[user_tier]["features"],
        "pdf_downloads_per_month": TIER_LIMITS[user_tier]["pdf_downloads_per_month"],
        "user_info": {
            "email": current_user["email"],
            "full_name": current_user["full_name"],
            "is_verified": current_user["is_verified"]
        }
    }

@router.get("/tiers/all")
async def get_all_tiers():
    """Get information about all available tiers (public endpoint)"""
    return {
        tier.value: {
            "name": tier.value.title(),
            "description": info["description"],
            "features": info["features"],
            "pdf_downloads": "Unlimited" if info["pdf_downloads_per_month"] == -1 else f"{info['pdf_downloads_per_month']}/month"
        }
        for tier, info in TIER_LIMITS.items()
    }

@router.post("/user/check-access/{feature}")
async def check_user_access(feature: str, current_user: dict = Depends(get_current_user)):
    """Check if user has access to a specific feature (now requires authentication)"""
    user_tier = get_user_tier_enhanced(current_user["user_id"])
    has_access = check_feature_access(feature, user_tier)
    
    return {
        "feature": feature,
        "has_access": has_access,
        "user_tier": user_tier.value,
        "required_tier": "premium" if not has_access and feature in TIER_LIMITS[UserTier.PREMIUM]["features"] else "professional" if not has_access else None
    }

# Utility functions for your existing code
def check_feature_access(feature_name: str, user_tier: UserTier = UserTier.FREE) -> bool:
    """Check if user tier has access to specific feature (keeping your existing function)"""
    allowed_features = TIER_LIMITS[user_tier]["features"]
    return feature_name in allowed_features

def require_feature_access_auth(feature_name: str):
    """Enhanced feature access dependency that uses authentication"""
    def check_access(current_user: dict = Depends(get_current_user)):
        user_tier = get_user_tier_enhanced(current_user["user_id"])
        if not check_feature_access(feature_name, user_tier):
            raise HTTPException(
                status_code=403, 
                detail={
                    "error": f"Feature '{feature_name}' requires premium subscription",
                    "required_tier": "premium" if feature_name in TIER_LIMITS[UserTier.PREMIUM]["features"] else "professional",
                    "current_tier": user_tier.value,
                    "upgrade_url": "/pricing"
                }
            )
        return current_user
    return check_access

# Initialize database on module import
init_database()