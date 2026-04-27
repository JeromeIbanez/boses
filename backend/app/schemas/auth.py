import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: Optional[str] = Field(default=None, max_length=200)
    company_name: str = Field(min_length=1, max_length=200)
    invite_token: str = Field(min_length=1, max_length=64)


class InviteTokenValidation(BaseModel):
    valid: bool
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)


class CompanyResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    slack_webhook_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    role: str
    is_boses_staff: bool
    email_notifications: bool = True
    company: CompanyResponse
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserResponse


class CompanyInviteValidation(BaseModel):
    valid: bool
    email: Optional[str] = None
    company_name: Optional[str] = None
    inviter_name: Optional[str] = None
    role: Optional[str] = None


class AcceptInviteRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=200)
    password: str = Field(min_length=8, max_length=72)
