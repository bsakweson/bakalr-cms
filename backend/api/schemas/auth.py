"""
Pydantic schemas for authentication
"""
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class OrganizationResponse(BaseModel):
    """Simple organization response for user objects"""
    id: int
    name: str
    slug: str
    
    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=8)
    organization_id: Optional[int] = None
    organization_name: str = Field(..., min_length=2, max_length=100, description="Organization name (required for registration)")
    full_name: Optional[str] = Field(None, description="Full name (will be split into first and last name)")


class UserLogin(BaseModel):
    """Schema for user login"""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: str
    
    def model_post_init(self, __context) -> None:
        """Validate that either email or username is provided"""
        if not self.email and not self.username:
            raise ValueError("Either email or username must be provided")


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None  # Alternative to first_name/last_name
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500, description="User bio/description")
    preferences: Optional[str] = Field(None, description="User preferences as JSON string")


class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    organization_id: int
    is_active: bool
    is_email_verified: bool
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    preferences: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []
    organization: Optional[OrganizationResponse] = None
    
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Schema for password change"""
    current_password: str
    new_password: str = Field(..., min_length=8)


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8)
