# NOTICE: This file is protected under RCF-PL
from fastapi import APIRouter, Depends

from app.models.user import User
from app.schemas.auth import UserResponse
from app.security import get_current_user

router = APIRouter(tags=["User"])


# [RCF:PROTECTED]
@router.get("/profile", response_model=UserResponse)
# [RCF:PROTECTED]
async def get_profile(current_user: User = Depends(get_current_user)):
    """Compact identity of the caller: id, email and display name.

    The User model has no `username` column, so this returns the same
    UserResponse that /api/auth/me serves instead of inventing a field.
    """
    return current_user
