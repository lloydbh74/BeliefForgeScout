from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import jwt
from datetime import datetime, timedelta
import os
from ..db.connection import get_db
from .security import (
    validate_jwt_secret,
    hash_password,
    verify_password,
    SecurityValidator,
    SecureInput,
    login_rate_limiter,
    audit_logger
)

router = APIRouter(tags=["authentication"])

# JWT Configuration
SECRET_KEY = validate_jwt_secret()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

security = HTTPBearer()

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    role: str

class UserResponse(BaseModel):
    email: str
    role: str
    permissions: list

# User credentials from environment variables
def get_admin_user():
    """Load admin user from environment variables"""
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        raise ValueError(
            "ADMIN_EMAIL and ADMIN_PASSWORD environment variables are required. "
            "Please set these in your .env file."
        )

    return {
        "email": admin_email,
        "password": hash_password(admin_password),  # Properly hashed password
        "role": "admin",
        "permissions": ["read", "write", "delete", "manage_settings", "manage_users"]
    }

# Load admin user
ADMIN_USER = get_admin_user()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        exp: int = payload.get("exp")

        if email is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if exp < datetime.utcnow().timestamp():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {"email": email, "role": role}

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    return verify_token(credentials)

def require_role(required_role: str):
    """Decorator to require specific role"""
    def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role")

        # Role hierarchy: admin > user
        role_hierarchy = {"admin": 3, "user": 2}

        if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        return current_user

    return role_checker

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def permission_checker(current_user: dict = Depends(get_current_user)):
        email = current_user.get("email")
        # Check if user is admin (only user we have)
        if email != ADMIN_USER["email"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )

        permissions = ADMIN_USER["permissions"]
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )

        return current_user

    return permission_checker

@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, request: Request):
    """Authenticate user and return JWT token"""
    try:
        email = login_data.email
        password = login_data.password

        # Validate input
        if not SecurityValidator.validate_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )

        # Get client IP for logging and rate limiting
        client_ip = request.client.host

        # Check rate limiting
        is_limited, remaining_time = login_rate_limiter.is_rate_limited(client_ip)
        if is_limited:
            audit_logger.log_auth_event(
                "RATE_LIMIT_EXCEEDED", email, client_ip, False,
                f"Locked out for {remaining_time} seconds"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many login attempts. Try again in {remaining_time // 60} minutes.",
                headers={"Retry-After": str(remaining_time)}
            )

        # Verify user credentials
        is_valid = email == ADMIN_USER["email"] and verify_password(password, ADMIN_USER["password"])

        if not is_valid:
            # Record failed attempt
            login_rate_limiter.is_rate_limited(client_ip)  # This will record the attempt
            if audit_logger:
                audit_logger.log_auth_event(
                    "LOGIN_FAILED", email, client_ip, False,
                    "Invalid credentials"
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": email, "role": ADMIN_USER["role"]},
            expires_delta=access_token_expires
        )

        # Log successful login
        audit_logger.log_auth_event(
            "LOGIN_SUCCESS", email, client_ip, True,
            f"Role: {ADMIN_USER['role']}"
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
            "role": ADMIN_USER["role"]
        }

    except HTTPException:
        raise
    except Exception as e:
        audit_logger.log_auth_event(
            "LOGIN_ERROR", email, request.client.host, False,
            str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to server error"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """Refresh JWT token"""
    try:
        email = current_user["email"]

        # Verify user is still our admin user
        if email != ADMIN_USER["email"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Create new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": email, "role": ADMIN_USER["role"]},
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
            "role": ADMIN_USER["role"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    try:
        email = current_user["email"]

        # Verify user is still our admin user
        if email != ADMIN_USER["email"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {
            "email": email,
            "role": ADMIN_USER["role"],
            "permissions": ADMIN_USER["permissions"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user info: {str(e)}"
        )

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user (client-side token invalidation)"""
    try:
        # In a stateless JWT implementation, logout is typically handled client-side
        # by simply removing the token from storage

        return {
            "message": "Successfully logged out",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )

@router.get("/validate")
async def validate_token(current_user: dict = Depends(get_current_user)):
    """Validate if current token is still valid"""
    try:
        return {
            "valid": True,
            "email": current_user["email"],
            "role": current_user["role"],
            "expires_at": datetime.utcnow() + timedelta(minutes=5)  # Mock expiry check
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token validation failed: {str(e)}"
        )

# Rate limiting middleware (basic implementation)
login_attempts = {}
MAX_ATTEMPTS = 5
LOCKOUT_DURATION = 15  # minutes

def check_rate_limit(email: str):
    """Check if user has exceeded login attempts"""
    now = datetime.utcnow()

    if email in login_attempts:
        attempts, lockout_until = login_attempts[email]

        if lockout_until and now < lockout_until:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account locked. Try again in {int((lockout_until - now).total_seconds())} seconds"
            )

        # Reset attempts if lockout has expired
        if lockout_until and now >= lockout_until:
            del login_attempts[email]

    return True

def record_login_attempt(email: str, success: bool):
    """Record login attempt for rate limiting"""
    now = datetime.utcnow()

    if success:
        # Clear failed attempts on successful login
        if email in login_attempts:
            del login_attempts[email]
    else:
        if email not in login_attempts:
            login_attempts[email] = [0, None]

        login_attempts[email][0] += 1

        # Apply lockout if max attempts reached
        if login_attempts[email][0] >= MAX_ATTEMPTS:
            lockout_until = now + timedelta(minutes=LOCKOUT_DURATION)
            login_attempts[email][1] = lockout_until

# Enhanced login endpoint with rate limiting
@router.post("/login-with-rate-limit", response_model=TokenResponse)
async def login_with_rate_limit(login_data: LoginRequest):
    """Login with rate limiting protection"""
    try:
        email = login_data.email
        password = login_data.password

        # Check rate limit
        check_rate_limit(email)

        # Verify credentials
        success = email == ADMIN_USER["email"] and verify_password(password, ADMIN_USER["password"])

        # Record attempt
        record_login_attempt(email, success)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": email, "role": ADMIN_USER["role"]},
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "role": ADMIN_USER["role"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )