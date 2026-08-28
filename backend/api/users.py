"""Users API endpoints.
Handles user profile management and settings.
"""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr

from api.dependencies import require_principal

router = APIRouter(prefix="/api/users", tags=["users"])


class UpdateProfileRequest(BaseModel):
    """Update profile request model."""

    name: str | None = None
    email: EmailStr | None = None
    preferences: dict[str, Any] | None = None


@router.get("/profile")
async def get_profile(principal: dict[str, Any] = Depends(require_principal)):
    """Get user profile information.

    Args:
        principal: Authenticated principal (verified JWT payload)

    Returns:
        User profile data

    """
    return {
        "id": "user_123",
        "email": "user@example.com",
        "name": "Demo User",
        "created_at": "2025-01-01T00:00:00Z",
        "license": {"type": "developer", "plugins": ["software", "healthcare"], "status": "active"},
        "preferences": {"theme": "dark", "notifications": True},
    }


@router.put("/profile")
async def update_profile(
    request: UpdateProfileRequest,
    principal: dict[str, Any] = Depends(require_principal),
):
    """Update user profile.

    Args:
        request: Profile update data
        principal: Authenticated principal (verified JWT payload)

    Returns:
        Updated profile

    """
    return {
        "success": True,
        "message": "Profile updated successfully",
        "profile": {
            "name": request.name or "Demo User",
            "email": request.email or "user@example.com",
            "preferences": request.preferences or {},
        },
    }


@router.get("/usage")
async def get_usage_stats(principal: dict[str, Any] = Depends(require_principal)):
    """Get user usage statistics.

    Args:
        principal: Authenticated principal (verified JWT payload)

    Returns:
        Usage statistics

    """
    return {
        "analyses_count": 42,
        "wizards_used": ["Enhanced Testing", "Performance Profiling", "Security Analysis"],
        "total_issues_found": 156,
        "period": "last_30_days",
    }


@router.delete("/account")
async def delete_account(principal: dict[str, Any] = Depends(require_principal)):
    """Delete user account.

    Args:
        principal: Authenticated principal (verified JWT payload)

    Returns:
        Deletion confirmation

    """
    return {
        "success": True,
        "message": "Account deletion initiated. You will receive a confirmation email.",
    }
