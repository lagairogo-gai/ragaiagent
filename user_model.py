from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class User(Base):
    """User model for authentication and user management"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # User status and role
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(String(20), default="user")  # user, manager, admin
    
    # Profile information
    avatar_url = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    organization = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    
    # Preferences and settings
    preferences = Column(JSON, default=dict)  # Store user preferences as JSON
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    projects = relationship("Project", back_populates="owner")
    user_stories = relationship("UserStory", back_populates="created_by_user")
    documents = relationship("Document", back_populates="uploaded_by")
    api_keys = relationship("ApiKey", back_populates="user")
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
    
    def to_dict(self):
        """Convert user to dictionary (excluding sensitive data)"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "role": self.role,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "organization": self.organization,
            "department": self.department,
            "preferences": self.preferences,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login": self.last_login
        }


class ApiKey(Base):
    """API Keys for programmatic access"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # Friendly name for the key
    key = Column(String(64), unique=True, index=True, nullable=False)
    
    # Owner and permissions
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permissions = Column(JSON, default=list)  # List of allowed operations
    
    # Status and usage
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    rate_limit_per_hour = Column(Integer, default=1000)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    def __repr__(self):
        return f"<ApiKey(name='{self.name}', user_id={self.user_id})>"
    
    def to_dict(self):
        """Convert API key to dictionary (excluding the actual key)"""
        return {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id,
            "permissions": self.permissions,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "expires_at": self.expires_at,
            "usage_count": self.usage_count,
            "rate_limit_per_hour": self.rate_limit_per_hour
        }


class UserSession(Base):
    """User session tracking"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    
    # Session metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    device_info = Column(JSON, nullable=True)
    
    # Session status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, active={self.is_active})>"


class UserIntegration(Base):
    """User integration settings for external services"""
    __tablename__ = "user_integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Integration details
    integration_type = Column(String(50), nullable=False)  # jira, confluence, sharepoint
    integration_name = Column(String(100), nullable=False)
    
    # Configuration
    config = Column(JSON, nullable=False)  # Store integration-specific config
    credentials = Column(JSON, nullable=True)  # Encrypted credentials
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # Whether connection is verified
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_sync = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<UserIntegration(user_id={self.user_id}, type='{self.integration_type}')>"
    
    def to_dict(self):
        """Convert integration to dictionary (excluding credentials)"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "integration_type": self.integration_type,
            "integration_name": self.integration_name,
            "config": self.config,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_sync": self.last_sync
        }