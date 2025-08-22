from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
import structlog

from ...core.database import get_db
from ...core.security import (
    authenticate_user, create_access_token, create_refresh_token,
    get_password_hash, verify_token, get_current_user,
    get_current_active_user, security, logout_user,
    create_api_key
)
from ...core.config import settings
from ...models.user import User, ApiKey, UserSession
from ...schemas.user import (
    UserCreate, UserResponse, UserUpdate, UserPasswordUpdate,
    LoginRequest, Token, RefreshTokenRequest, ApiKeyCreate,
    ApiKeyResponse, ApiKeyListResponse, UserProfile,
    PasswordResetRequest, PasswordResetConfirm
)

logger = structlog.get_logger()
router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    request: Request = None
):
    """Register a new user"""
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=user_data.role,
        organization=user_data.organization,
        department=user_data.department,
        is_active=True,
        is_verified=False  # Require email verification
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(
        "New user registered",
        user_id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        client_ip=request.client.host if request else None
    )
    
    return db_user


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
    request: Request = None
):
    """Authenticate user and return JWT tokens"""
    
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        logger.warning(
            "Failed login attempt",
            username=login_data.username,
            client_ip=request.client.host if request else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    # Create access and refresh tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=refresh_token_expires
    )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create user session record
    session = UserSession(
        user_id=user.id,
        session_token=access_token[:32],  # Store part of token for identification
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
        expires_at=datetime.utcnow() + access_token_expires
    )
    db.add(session)
    db.commit()
    
    logger.info(
        "User logged in successfully",
        user_id=user.id,
        username=user.username,
        client_ip=request.client.host if request else None
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    
    payload = verify_token(refresh_data.refresh_token, "refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username = payload.get("sub")
    user_id = payload.get("user_id")
    
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role},
        expires_delta=access_token_expires
    )
    
    logger.info("Token refreshed", user_id=user.id, username=user.username)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_data.refresh_token,  # Keep same refresh token
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Logout user by blacklisting current token"""
    
    token = credentials.credentials
    logout_user(token)
    
    # Deactivate user sessions
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True
    ).update({"is_active": False})
    db.commit()
    
    logger.info("User logged out", user_id=current_user.id, username=current_user.username)
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile information"""
    
    # Get additional profile statistics
    user_dict = current_user.to_dict()
    
    # Add project count
    user_dict["project_count"] = len(current_user.projects)
    
    # Add user story count
    user_dict["user_story_count"] = len(current_user.user_stories)
    
    # Add document count
    user_dict["document_count"] = len(current_user.documents)
    
    return user_dict


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile"""
    
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    logger.info("User profile updated", user_id=current_user.id, updated_fields=list(update_data.keys()))
    
    return current_user


@router.put("/me/password")
async def update_password(
    password_update: UserPasswordUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user's password"""
    
    from ...core.security import verify_password
    
    # Verify current password
    if not verify_password(password_update.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_update.new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info("User password updated", user_id=current_user.id)
    
    return {"message": "Password updated successfully"}


# API Key management
@router.post("/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_user_api_key(
    api_key_data: ApiKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new API key for current user"""
    
    # Generate API key
    key = create_api_key()
    
    # Create API key record
    db_api_key = ApiKey(
        name=api_key_data.name,
        key=key,
        user_id=current_user.id,
        permissions=api_key_data.permissions,
        rate_limit_per_hour=api_key_data.rate_limit_per_hour,
        expires_at=api_key_data.expires_at
    )
    
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    
    logger.info(
        "API key created",
        user_id=current_user.id,
        api_key_id=db_api_key.id,
        api_key_name=db_api_key.name
    )
    
    # Return response with the actual key (only shown once)
    response_data = db_api_key.to_dict()
    response_data["key"] = key
    
    return response_data


@router.get("/api-keys", response_model=List[ApiKeyListResponse])
async def list_user_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List current user's API keys"""
    
    api_keys = db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()
    return [key.to_dict() for key in api_keys]


@router.delete("/api-keys/{api_key_id}")
async def delete_api_key(
    api_key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an API key"""
    
    api_key = db.query(ApiKey).filter(
        ApiKey.id == api_key_id,
        ApiKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    db.delete(api_key)
    db.commit()
    
    logger.info(
        "API key deleted",
        user_id=current_user.id,
        api_key_id=api_key_id
    )
    
    return {"message": "API key deleted successfully"}


# Password reset (placeholder - would need email service integration)
@router.post("/password-reset-request")
async def request_password_reset(
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request password reset (placeholder)"""
    
    user = db.query(User).filter(User.email == reset_request.email).first()
    if not user:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a reset link has been sent"}
    
    # TODO: Implement email sending with reset token
    logger.info("Password reset requested", user_id=user.id, email=user.email)
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password-reset-confirm")
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm password reset (placeholder)"""
    
    # TODO: Implement token verification and password update
    logger.info("Password reset attempt", token=reset_confirm.token[:10] + "...")
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password reset not implemented yet"
    )


# User sessions
@router.get("/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's active sessions"""
    
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow()
    ).all()
    
    return [
        {
            "id": session.id,
            "ip_address": session.ip_address,
            "user_agent": session.user_agent,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "expires_at": session.expires_at
        }
        for session in sessions
    ]


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Revoke a specific session"""
    
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session.is_active = False
    db.commit()
    
    logger.info("Session revoked", user_id=current_user.id, session_id=session_id)
    
    return {"message": "Session revoked successfully"}