from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List
from app.core.security import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token
)
from app.database.db import get_db, init_database
from app.services.session_service import (
    create_session,
    validate_session,
    revoke_session,
    revoke_all_sessions,
    list_sessions
)
from jose import jwt, JWTError
import os
import uuid
import re
import sqlite3

router = APIRouter()
security = HTTPBearer(auto_error=False)


class UserTier(Enum):
    BASIC = "basic"
    FREE = "free"
    PREMIUM = "premium"
    PROFESSIONAL = "professional"


TIER_LIMITS = {
    UserTier.BASIC: {
        "pdf_downloads_per_month": 1,
        "features": ["resume_builder", "company_research"],
        "description": "Basic resume builder + Company research"
    },
    UserTier.FREE: {
        "pdf_downloads_per_month": 1,
        "features": ["resume_builder", "company_research"],
        "description": "Basic resume builder + Company research"
    },
    UserTier.PREMIUM: {
        "pdf_downloads_per_month": -1,
        "features": [
            "resume_builder", "company_research", "resume_analysis",
            "cover_letter_analysis", "linkedin_optimization", "interview_practice",
            "ats_scoring", "job_customization"
        ],
        "description": "Premium - AI Analysis + Cover Letters + Interview Prep"
    },
    UserTier.PROFESSIONAL: {
        "pdf_downloads_per_month": -1,
        "features": [
            "resume_builder", "company_research", "resume_analysis",
            "cover_letter_analysis", "linkedin_optimization", "interview_practice",
            "ats_scoring", "job_customization", "mock_interview_simulator",
            "career_path_analysis", "salary_benchmarking", "skills_gap_analysis"
        ],
        "description": "Professional - Everything + AI Mock Interviews + Career Analysis"
    }
}


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


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


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


class SessionResponse(BaseModel):
    session_id: str
    created_at: datetime
    last_used: datetime
    expires_at: datetime
    is_active: bool


class EmailVerificationRequest(BaseModel):
    email: EmailStr


def parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def user_response(user: Dict) -> UserResponse:
    return UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        full_name=user["full_name"],
        tier=user.get("tier") or UserTier.BASIC.value,
        is_verified=bool(user.get("is_verified")),
        created_at=parse_dt(user["created_at"]),
        last_login=parse_dt(user.get("last_login"))
    )


def create_user_db(user_data: UserCreate) -> str:
    user_id = str(uuid.uuid4())
    password_hash = get_password_hash(user_data.password)

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (user_id, email, password_hash, full_name, tier)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, user_data.email.lower(), password_hash, user_data.full_name, UserTier.BASIC.value))
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )


def get_user_by_email(email: str) -> Optional[Dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND is_active = TRUE", (email.lower(),))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[Dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ? AND is_active = TRUE", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_user_login_time(user_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET last_login = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (user_id,))
        conn.commit()


def get_user_tier_enhanced(user_id: Optional[str] = None) -> UserTier:
    if not user_id:
        return UserTier.BASIC

    if os.getenv("DEMO_PREMIUM") == "true":
        return UserTier.PREMIUM

    user = get_user_by_id(user_id)
    if user:
        try:
            return UserTier(user.get('tier') or UserTier.BASIC.value)
        except ValueError:
            return UserTier.BASIC

    return UserTier.BASIC


def decode_jwt_token(token: str, expected_type: str) -> Dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token type. Expected {expected_type} token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def issue_tokens(user_id: str):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user_id}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data={"sub": user_id})
    create_session(user_id, refresh_token)
    return access_token, refresh_token


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_jwt_token(credentials.credentials, expected_type="access")
    user = get_user_by_id(payload["sub"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.post("/auth/register", response_model=TokenResponse)
async def register_user(user_data: UserCreate):
    try:
        user_id = create_user_db(user_data)
        access_token, refresh_token = issue_tokens(user_id)
        user = get_user_by_id(user_id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_response(user)
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed")


@router.post("/auth/login", response_model=TokenResponse)
async def login_user(user_credentials: UserLogin):
    user = get_user_by_email(user_credentials.email)
    if not user or not verify_password(user_credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    update_user_login_time(user["user_id"])
    access_token, refresh_token = issue_tokens(user["user_id"])
    fresh_user = get_user_by_id(user["user_id"])

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response(fresh_user)
    )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_auth_tokens(refresh_data: RefreshTokenRequest):
    payload = decode_jwt_token(refresh_data.refresh_token, expected_type="refresh")
    user_id = payload["sub"]

    if not validate_session(user_id, refresh_data.refresh_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session is invalid or expired")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    revoke_session(refresh_data.refresh_token)
    access_token, refresh_token = issue_tokens(user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response(user)
    )


@router.post("/auth/logout")
async def logout_user(logout_data: LogoutRequest):
    if logout_data.refresh_token:
        revoke_session(logout_data.refresh_token)
    return {"success": True, "message": "Logged out successfully"}


@router.post("/auth/logout-all")
async def logout_all_user_sessions(current_user: dict = Depends(get_current_user)):
    revoked_count = revoke_all_sessions(current_user["user_id"])
    return {"success": True, "message": "All sessions logged out successfully", "revoked_sessions": revoked_count}


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return user_response(current_user)


@router.get("/auth/sessions", response_model=List[SessionResponse])
async def get_auth_sessions(current_user: dict = Depends(get_current_user)):
    rows = list_sessions(current_user["user_id"])
    return [
        SessionResponse(
            session_id=row["session_id"],
            created_at=parse_dt(row["created_at"]),
            last_used=parse_dt(row["last_used"]),
            expires_at=parse_dt(row["expires_at"]),
            is_active=bool(row["is_active"])
        )
        for row in rows
    ]


@router.get("/user/tier")
async def get_user_tier_info(current_user: dict = Depends(get_current_user)):
    user_tier = get_user_tier_enhanced(current_user["user_id"])
    return {
        "current_tier": "basic" if user_tier == UserTier.FREE else user_tier.value,
        "description": TIER_LIMITS[user_tier]["description"],
        "features": TIER_LIMITS[user_tier]["features"],
        "pdf_downloads_per_month": TIER_LIMITS[user_tier]["pdf_downloads_per_month"],
        "user_info": {
            "email": current_user["email"],
            "full_name": current_user["full_name"],
            "is_verified": bool(current_user["is_verified"])
        }
    }


@router.get("/tiers/all")
async def get_all_tiers():
    return {
        "basic": {
            "name": "Basic",
            "description": TIER_LIMITS[UserTier.BASIC]["description"],
            "features": TIER_LIMITS[UserTier.BASIC]["features"],
            "pdf_downloads": "1/month"
        },
        "premium": {
            "name": "Premium",
            "description": TIER_LIMITS[UserTier.PREMIUM]["description"],
            "features": TIER_LIMITS[UserTier.PREMIUM]["features"],
            "pdf_downloads": "Unlimited"
        },
        "professional": {
            "name": "Professional",
            "description": TIER_LIMITS[UserTier.PROFESSIONAL]["description"],
            "features": TIER_LIMITS[UserTier.PROFESSIONAL]["features"],
            "pdf_downloads": "Unlimited"
        }
    }


def check_feature_access(feature_name: str, user_tier: UserTier = UserTier.BASIC) -> bool:
    allowed_features = TIER_LIMITS[user_tier]["features"]
    return feature_name in allowed_features


def require_feature_access_auth(feature_name: str):
    def check_access(current_user: dict = Depends(get_current_user)):
        user_tier = get_user_tier_enhanced(current_user["user_id"])
        if not check_feature_access(feature_name, user_tier):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": f"Feature '{feature_name}' requires a higher subscription",
                    "current_tier": "basic" if user_tier == UserTier.FREE else user_tier.value,
                    "upgrade_url": "/pricing"
                }
            )
        return current_user
    return check_access


init_database()
