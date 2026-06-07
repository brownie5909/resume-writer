# Admin management routes for Hire Ready

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .user_management import get_current_user, get_db, get_user_by_id

router = APIRouter()

VALID_ADMIN_TIERS = ["basic", "premium", "professional"]
LEGACY_BASIC_TIERS = ["basic", "free"]


def require_admin_access(current_user: dict = Depends(get_current_user)):
    """Require admin access using the is_admin flag stored in the users table."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT is_admin, is_active
            FROM users
            WHERE user_id = ?
            """,
            (current_user["user_id"],),
        )
        result = cursor.fetchone()

        if not result:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not found")

        is_admin, is_active = result
        if not is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
        if not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    return current_user


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    tier: Optional[str] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None


class AdminStats(BaseModel):
    total_users: int
    basic_users: int
    free_users: int
    premium_users: int
    professional_users: int
    verified_users: int
    active_users: int
    monthly_signups: int
    revenue_estimate: float


class UserResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    tier: str
    is_verified: bool
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    stripe_customer_id: Optional[str]


def parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


@router.get("/admin/stats", response_model=AdminStats)
async def get_admin_stats(admin_user: dict = Depends(require_admin_access)):
    """Get admin statistics for the internal admin dashboard."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT tier, COUNT(*) FROM users WHERE is_active = TRUE GROUP BY tier")
        tier_counts = dict(cursor.fetchall())

        cursor.execute("SELECT COUNT(*) FROM users WHERE is_verified = TRUE AND is_active = TRUE")
        verified_users = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*) FROM users
            WHERE last_login > datetime('now', '-30 days') AND is_active = TRUE
            """
        )
        active_users = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*) FROM users
            WHERE created_at > datetime('now', '-30 days') AND is_active = TRUE
            """
        )
        monthly_signups = cursor.fetchone()[0]

        basic_users = sum(tier_counts.get(tier, 0) for tier in LEGACY_BASIC_TIERS)
        premium_users = tier_counts.get("premium", 0)
        pro_users = tier_counts.get("professional", 0)
        revenue_estimate = (premium_users * 19) + (pro_users * 39)

    return AdminStats(
        total_users=total_users,
        basic_users=basic_users,
        free_users=basic_users,
        premium_users=premium_users,
        professional_users=pro_users,
        verified_users=verified_users,
        active_users=active_users,
        monthly_signups=monthly_signups,
        revenue_estimate=revenue_estimate,
    )


@router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(
    admin_user: dict = Depends(require_admin_access),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    verified: Optional[bool] = Query(None),
):
    """Get active users with filtering and pagination."""
    offset = (page - 1) * limit
    conditions = ["is_active = TRUE"]
    params = []

    if search:
        conditions.append("(full_name LIKE ? OR email LIKE ?)")
        search_term = f"%{search}%"
        params.extend([search_term, search_term])

    if tier:
        if tier == "basic":
            conditions.append("tier IN (?, ?)")
            params.extend(LEGACY_BASIC_TIERS)
        else:
            conditions.append("tier = ?")
            params.append(tier)

    if verified is not None:
        conditions.append("is_verified = ?")
        params.append(verified)

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT user_id, email, full_name, tier, is_verified, is_active,
               created_at, last_login, stripe_customer_id
        FROM users
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params + [limit, offset])
        rows = cursor.fetchall()

    users = []
    for row in rows:
        tier_value = row[3] or "basic"
        users.append(
            UserResponse(
                user_id=row[0],
                email=row[1],
                full_name=row[2],
                tier="basic" if tier_value == "free" else tier_value,
                is_verified=bool(row[4]),
                is_active=bool(row[5]),
                created_at=parse_datetime(row[6]),
                last_login=parse_datetime(row[7]),
                stripe_customer_id=row[8],
            )
        )

    return users


@router.get("/admin/users/{user_id}")
async def get_user_details(user_id: str, admin_user: dict = Depends(require_admin_access)):
    """Get detailed information about a specific user."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT feature_name, usage_count, month_year
            FROM usage_tracking
            WHERE user_id = ?
            ORDER BY month_year DESC
            """,
            (user_id,),
        )
        usage_stats = cursor.fetchall()

        cursor.execute(
            """
            SELECT created_at, last_used, is_active
            FROM user_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (user_id,),
        )
        sessions = cursor.fetchall()

    tier_value = user.get("tier") or "basic"
    return {
        "user": UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            full_name=user["full_name"],
            tier="basic" if tier_value == "free" else tier_value,
            is_verified=bool(user["is_verified"]),
            is_active=bool(user["is_active"]),
            created_at=parse_datetime(user["created_at"]),
            last_login=parse_datetime(user.get("last_login")),
            stripe_customer_id=user.get("stripe_customer_id"),
        ),
        "usage_statistics": [
            {"feature": stat[0], "count": stat[1], "month": stat[2]}
            for stat in usage_stats
        ],
        "recent_sessions": [
            {"created_at": session[0], "last_used": session[1], "is_active": bool(session[2])}
            for session in sessions
        ],
    }


@router.put("/admin/users/{user_id}")
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    admin_user: dict = Depends(require_admin_access),
):
    """Update user information."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_fields = []
    params = []

    if user_update.full_name is not None:
        update_fields.append("full_name = ?")
        params.append(user_update.full_name)

    if user_update.tier is not None:
        if user_update.tier not in VALID_ADMIN_TIERS:
            raise HTTPException(status_code=400, detail="Invalid tier")
        update_fields.append("tier = ?")
        params.append(user_update.tier)

    if user_update.is_verified is not None:
        update_fields.append("is_verified = ?")
        params.append(user_update.is_verified)

    if user_update.is_active is not None:
        update_fields.append("is_active = ?")
        params.append(user_update.is_active)

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(user_id)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            UPDATE users
            SET {', '.join(update_fields)}
            WHERE user_id = ?
            """,
            params,
        )
        conn.commit()

    return {"success": True, "message": "User updated successfully"}


@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, admin_user: dict = Depends(require_admin_access)):
    """Soft delete a user."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id == admin_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (user_id,),
        )
        conn.commit()

    return {"success": True, "message": "User deactivated successfully"}


@router.post("/admin/users/{user_id}/change-tier")
async def change_user_tier(
    user_id: str,
    new_tier: str,
    admin_user: dict = Depends(require_admin_access),
):
    """Change a user's subscription tier."""
    if new_tier not in VALID_ADMIN_TIERS:
        raise HTTPException(status_code=400, detail="Invalid tier")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_tier = user["tier"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET tier = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (new_tier, user_id),
        )
        conn.commit()

    return {
        "success": True,
        "message": f"User tier changed from {old_tier} to {new_tier}",
        "old_tier": old_tier,
        "new_tier": new_tier,
    }
