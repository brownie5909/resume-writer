from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from enum import Enum
from typing import Optional
import os
from fastapi import Form

router = APIRouter()
security = HTTPBearer(auto_error=False)

class UserTier(Enum):
    FREE = "free"
    PREMIUM = "premium" 
    PROFESSIONAL = "professional"

# Tier limits and permissions based on your pricing plan
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

def get_user_tier(user_id: Optional[str] = None) -> UserTier:
    """
    Determine user tier. For now, return FREE for all users.
    TODO: Implement database lookup when ready for premium
    """
    if not user_id:
        return UserTier.FREE
    
    # Temporary: Allow premium access for testing
    # You can test premium features by setting user_id to "premium_user" or "pro_user"
    if user_id == "premium_user":
        return UserTier.PREMIUM
    elif user_id == "pro_user":
        return UserTier.PROFESSIONAL
    elif os.getenv("DEMO_PREMIUM") == "true":
        return UserTier.PREMIUM
    
    return UserTier.FREE

def check_feature_access(feature_name: str, user_tier: UserTier = UserTier.FREE) -> bool:
    """Check if user tier has access to specific feature"""
    allowed_features = TIER_LIMITS[user_tier]["features"]
    return feature_name in allowed_features

def require_feature_access(feature_name: str):
    """Dependency to check feature access - returns user tier if access granted"""
    def check_access(user_id: Optional[str] = Form(None)):  # Add Form(None) here
        user_tier = get_user_tier(user_id)
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
        return user_tier
    return check_access

# API endpoints for tier management
@router.get("/user/tier")
async def get_user_tier_info(user_id: Optional[str] = None):
    """Get current user tier and feature access"""
    user_tier = get_user_tier(user_id)
    
    return {
        "current_tier": user_tier.value,
        "description": TIER_LIMITS[user_tier]["description"],
        "features": TIER_LIMITS[user_tier]["features"],
        "pdf_downloads_per_month": TIER_LIMITS[user_tier]["pdf_downloads_per_month"]
    }

@router.get("/tiers/all")
async def get_all_tiers():
    """Get information about all available tiers"""
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
async def check_user_access(feature: str, user_id: Optional[str] = None):
    """Check if user has access to a specific feature"""
    user_tier = get_user_tier(user_id)
    has_access = check_feature_access(feature, user_tier)
    
    return {
        "feature": feature,
        "has_access": has_access,
        "user_tier": user_tier.value,
        "required_tier": "premium" if not has_access and feature in TIER_LIMITS[UserTier.PREMIUM]["features"] else None
    }
