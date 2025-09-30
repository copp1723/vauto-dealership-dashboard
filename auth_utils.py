#!/usr/bin/env python3
"""
Shared authentication utilities for the dashboard application
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from database import User, UserRole, get_database_manager
import os

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-" + os.urandom(16).hex())
ALGORITHM = "HS256"

# Security
security = HTTPBearer()

# Initialize database manager
db_manager = get_database_manager()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_value = credentials.credentials
        if not token_value:
            raise credentials_exception
        payload = jwt.decode(token_value, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    with db_manager.get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if user is None or not user.is_active:
            raise credentials_exception
        return user


def get_current_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure current user is super admin"""
    if current_user.role_enum != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


def get_current_admin_or_higher(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure current user is admin or super admin"""
    if current_user.role_enum not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or super admin access required"
        )
    return current_user
