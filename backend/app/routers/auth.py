# NOTICE: This file is protected under RCF-PL
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    decode_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
    mark_refresh_token_used,
    revoke_refresh_token,
)
from app.limiter import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


# [RCF:PROTECTED]
@limiter.limit("5/minute")
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
# [RCF:PROTECTED]
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=body.email, password_hash=hash_password(body.password), name=body.name)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(user.id)
    refresh_token, jti = create_refresh_token(user.id)
    # Persist the refresh token
    db.add(RefreshToken(
        jti=jti,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    ))
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


# [RCF:PROTECTED]
@limiter.limit("10/minute")
@router.post("/login", response_model=TokenResponse)
# [RCF:PROTECTED]
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user.id)
    refresh_token, jti = create_refresh_token(user.id)
    # Persist the refresh token
    db.add(RefreshToken(
        jti=jti,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    ))
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


# [RCF:PROTECTED]
@limiter.limit("10/minute")
@router.post("/refresh", response_model=TokenResponse)
# [RCF:PROTECTED]
async def refresh(request: Request, body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_refresh_token(body.refresh_token)
    user_id = int(payload["sub"])
    jti = payload["jti"]

    # Verify the token exists and is not revoked/used
    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if record.revoked:
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    if record.used:
        raise HTTPException(status_code=401, detail="Refresh token already used")
    if record.user_id != user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Mark old token as used
    await mark_refresh_token_used(jti, db)

    # Issue new tokens
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(user.id)
    new_refresh_token, new_jti = create_refresh_token(user.id)
    # Persist the new refresh token
    db.add(RefreshToken(
        jti=new_jti,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    ))
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


# [RCF:PROTECTED]
@router.post("/logout", status_code=status.HTTP_200_OK)
# [RCF:PROTECTED]
async def logout(request: Request, body: RefreshRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    payload = decode_refresh_token(body.refresh_token)
    jti = payload["jti"]
    # Ensure token belongs to current user
    if int(payload["sub"]) != user.id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    await revoke_refresh_token(jti, db)
    return {"detail": "Successfully logged out"}


# [RCF:PROTECTED]
@router.get("/me", response_model=UserResponse)
# [RCF:PROTECTED]
async def me(user: User = Depends(get_current_user)):
    return user