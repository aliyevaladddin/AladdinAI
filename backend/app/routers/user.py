from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.security import get_current_user

router = APIRouter()

@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return {"username": current_user.username, "email": current_user.email}
