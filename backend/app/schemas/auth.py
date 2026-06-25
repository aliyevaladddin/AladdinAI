# NOTICE: This file is protected under RCF-PL
from pydantic import BaseModel, EmailStr


# [RCF:PROTECTED]
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


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
