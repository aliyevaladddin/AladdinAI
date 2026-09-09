# NOTICE: This file is protected under RCF-PL
from pydantic import BaseModel, EmailStr, Field


# [RCF:PROTECTED]
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=100)


# [RCF:PROTECTED]
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# [RCF:PROTECTED]
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# [RCF:PROTECTED]
class RefreshRequest(BaseModel):
    refresh_token: str


# [RCF:PROTECTED]
class UserResponse(BaseModel):
    id: int
    email: str
    name: str

    model_config = {"from_attributes": True}
