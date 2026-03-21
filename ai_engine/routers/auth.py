"""
Authentication endpoints: sign-up, sign-in, sign-out, token refresh.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Header
from typing import Optional
from uuid import UUID
from datetime import datetime

from ..models.receiver import UserCreate, UserSignIn, User, TokenPair, TokenData
from ..services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    extract_user_from_token,
)
from ..services.database import fetch_one, fetch_all, execute_query

router = APIRouter(prefix="/api/auth", tags=["authentication"])


async def get_current_user(authorization: Optional[str] = Header(None)) -> User:
    """
    Dependency to extract and validate current user from JWT token.

    Expects: Authorization: Bearer <token>
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]
    user_data = extract_user_from_token(token)

    if not user_data or not user_data.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    user_row = await fetch_one(
        "SELECT * FROM users WHERE id = $1 AND is_active = true",
        user_data["user_id"]
    )

    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return User(**user_row)


@router.post("/sign-up", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def sign_up(user_data: UserCreate):
    """
    Create a new user account.

    Returns:
        Access token and refresh token
    """
    # Check if user already exists
    existing = await fetch_one(
        "SELECT id FROM users WHERE email = $1 OR username = $2",
        user_data.email,
        user_data.username
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )

    # Hash password
    password_hash = hash_password(user_data.password)

    # Insert user
    user_row = await fetch_one(
        """
        INSERT INTO users (email, username, password_hash, full_name, role)
        VALUES ($1, $2, $3, $4, 'student')
        RETURNING id, email, username, full_name, role, is_active, created_at, updated_at
        """,
        user_data.email,
        user_data.username,
        password_hash,
        user_data.full_name
    )

    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

    # Create tokens
    token_data = {
        "user_id": str(user_row["id"]),
        "username": user_row["username"],
        "role": user_row["role"],
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"user_id": str(user_row["id"])})

    # Store refresh token hash in sessions
    from ai_engine.services.auth import JWT_SECRET_KEY
    import hashlib
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    await execute_query(
        """
        INSERT INTO sessions (user_id, token_hash, expires_at)
        VALUES ($1, $2, NOW() + INTERVAL '7 days')
        """,
        user_row["id"],
        token_hash
    )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/sign-in", response_model=TokenPair)
async def sign_in(credentials: UserSignIn):
    """
    Sign in with email/username and password.

    Returns:
        Access token and refresh token
    """
    # Find user by email or username
    user_row = await fetch_one(
        """
        SELECT id, email, username, password_hash, full_name, role,
               is_active, created_at, updated_at
        FROM users
        WHERE (email = $1 OR username = $1) AND is_active = true
        """,
        credentials.email_or_username
    )

    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password"
        )

    # Verify password
    if not verify_password(credentials.password, user_row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password"
        )

    # Create tokens
    token_data = {
        "user_id": str(user_row["id"]),
        "username": user_row["username"],
        "role": user_row["role"],
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"user_id": str(user_row["id"])})

    # Store refresh token hash in sessions
    import hashlib
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    await execute_query(
        """
        INSERT INTO sessions (user_id, token_hash, expires_at)
        VALUES ($1, $2, NOW() + INTERVAL '7 days')
        """,
        user_row["id"],
        token_hash
    )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/sign-out")
async def sign_out(
    current_user: User = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    """
    Sign out current user by invalidating the refresh token.
    """
    # Extract refresh token from request if provided
    # For now, just return success
    # TODO: Track and invalidate specific refresh tokens

    return {"message": "Successfully signed out"}


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Returns:
        User object
    """
    return current_user


@router.post("/refresh", response_model=TokenPair)
async def refresh_access_token(refresh_token: str):
    """
    Refresh access token using a valid refresh token.

    Args:
        refresh_token: The refresh token

    Returns:
        New access token and refresh token
    """
    # Decode refresh token
    user_data = extract_user_from_token(refresh_token)

    if not user_data or not user_data.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Fetch user to verify they still exist
    user_row = await fetch_one(
        "SELECT * FROM users WHERE id = $1 AND is_active = true",
        user_data["user_id"]
    )

    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Create new tokens
    token_data = {
        "user_id": str(user_row["id"]),
        "username": user_row["username"],
        "role": user_row["role"],
    }

    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token({"user_id": str(user_row["id"])})

    return TokenPair(
        access_token=new_access_token,
        refresh_token=new_refresh_token
    )
