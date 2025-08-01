from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from enum import Enum
from typing import Optional
import os

router = APIRouter()
security = HTTPBearer(auto_error=False)

class UserTier(Enum):
    FREE = "free"
    PREMIUM = "premium" 
    PROFESSIONAL = "professional"

# Tier limits and permissions
TIER_LIMITS = {
    UserTier.FREE: {
        "pdf_downloads_per_month": 1,
        "features": ["resume_builder", "company_research"]
    },
    UserTier.PREMIUM: {
        "pdf_downloads_per_month": -1,  # Unlimited
        "features": ["resume_builder", "company_research", "resume_analysis", 
                    "cover_letter_analysis", "interview_practice", "linkedin_optimization"]
    },
    UserTier.PROFESSIONAL: {
        "pdf_downloads_per_month": -1,  # Unlimited
        "features": ["all"]  # All features
    }
}

def get_user_tier(user_id: Optional[str] = None) -> UserTier:
    """
    Determine user tier. For now, return FREE for all users.
    TODO: Implement database lookup when ready for premium
    """
    if not user_id:
        return UserTier.FREE
    
    # Temporary: Check for premium access via URL or special user_id
    if user_id == "premium_user" or os.getenv("DEMO_PREMIUM") == "true":
        return UserTier.PREMIUM
    
    return UserTier.FREE

def check_feature_access(feature_name: str, user_tier: UserTier = UserTier.FREE) -> bool:
    """Check if user tier has access to specific feature"""
    allowed_features = TIER_LIMITS[user_tier]["features"]
    
    if "all" in allowed_features:
        return True
    
    return feature_name in allowed_features

def require_feature_access(feature_name: str):
    """Dependency to check feature access"""
    def check_access(user_id: Optional[str] = None):
        user_tier = get_user_tier(user_id)
        if not check_feature_access(feature_name, user_tier):
            raise HTTPException(
                status_code=403, 
                detail=f"Feature '{feature_name}' requires premium subscription"
            )
        return user_tier
    return check_access
