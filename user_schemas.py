from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""
    username: str
    email: EmailStr
    full_name: str
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if not v.isalnum() and '_' not in v and '-' not in v:
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str
    role: Optional[str] = "user"
    organization: Optional[str] = None
    department: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    organization: Optional[str] = None
    department: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    
    @validator('bio')
    def validate_bio(cls, v):
        if v and len(v) > 500:
            raise ValueError('Bio must be less than 500 characters')
        return v


class UserPasswordUpdate(BaseModel):
    """Schema for updating user password"""
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserResponse(UserBase):
    """Schema for user response (public information)"""
    id: int
    is_active: bool
    is_verified: bool
    role: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    organization: Optional[str] = None
    department: Optional[str] = None
    preferences: Dict[str, Any] = {}
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserProfile(UserResponse):
    """Extended user profile with additional information"""
    project_count: Optional[int] = 0
    user_story_count: Optional[int] = 0
    document_count: Optional[int] = 0


# Authentication schemas
class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token payload data"""
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request schema"""
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


# API Key schemas
class ApiKeyBase(BaseModel):
    """Base API key schema"""
    name: str
    permissions: List[str] = []
    rate_limit_per_hour: Optional[int] = 1000
    expires_at: Optional[datetime] = None


class ApiKeyCreate(ApiKeyBase):
    """Schema for creating API key"""
    pass


class ApiKeyUpdate(BaseModel):
    """Schema for updating API key"""
    name: Optional[str] = None
    permissions: Optional[List[str]] = None
    rate_limit_per_hour: Optional[int] = None
    is_active: Optional[bool] = None


class ApiKeyResponse(ApiKeyBase):
    """API key response schema"""
    id: int
    key: str  # Only shown on creation
    user_id: int
    is_active: bool
    created_at: datetime
    last_used: Optional[datetime] = None
    usage_count: int
    
    class Config:
        from_attributes = True


class ApiKeyListResponse(BaseModel):
    """API key list response (without the actual key)"""
    id: int
    name: str
    permissions: List[str]
    is_active: bool
    created_at: datetime
    last_used: Optional[datetime] = None
    usage_count: int
    rate_limit_per_hour: int
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# User Integration schemas
class UserIntegrationBase(BaseModel):
    """Base user integration schema"""
    integration_type: str
    integration_name: str
    config: Dict[str, Any]


class UserIntegrationCreate(UserIntegrationBase):
    """Schema for creating user integration"""
    credentials: Optional[Dict[str, Any]] = None


class UserIntegrationUpdate(BaseModel):
    """Schema for updating user integration"""
    integration_name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class UserIntegrationResponse(UserIntegrationBase):
    """User integration response schema"""
    id: int
    user_id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# User preferences schemas
class UserPreferences(BaseModel):
    """User preferences schema"""
    theme: Optional[str] = "light"
    language: Optional[str] = "en"
    timezone: Optional[str] = "UTC"
    email_notifications: Optional[bool] = True
    push_notifications: Optional[bool] = True
    default_llm_provider: Optional[str] = None
    default_llm_model: Optional[str] = None
    rag_settings: Optional[Dict[str, Any]] = {}
    ui_settings: Optional[Dict[str, Any]] = {}


# User list and search schemas
class UserListParams(BaseModel):
    """Parameters for listing users"""
    skip: int = 0
    limit: int = 100
    search: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    organization: Optional[str] = None


class UserListResponse(BaseModel):
    """Response for user list"""
    users: List[UserResponse]
    total: int
    skip: int
    limit: int


# Password reset schemas
class PasswordResetRequest(BaseModel):
    """Password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


# User verification schemas
class EmailVerificationRequest(BaseModel):
    """Email verification request"""
    email: EmailStr


class EmailVerificationConfirm(BaseModel):
    """Email verification confirmation"""
    token: str


# User statistics schema
class UserStats(BaseModel):
    """User statistics"""
    total_projects: int
    active_projects: int
    total_user_stories: int
    completed_user_stories: int
    total_documents: int
    processed_documents: int
    last_activity: Optional[datetime] = None
    account_age_days: int