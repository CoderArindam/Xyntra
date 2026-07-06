import logging
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from typing import List

from app.schemas.auth import (
    OrganizationCreate,
    OrganizationRegistrationResponse,
    UserLogin,
    SuccessResponse,
    UserResponse,
    SessionResponse,
    SecurityEventResponse,
    PasswordPolicy
)
from app.auth.jwt import create_access_token
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False, # Set to True in production with HTTPS
        samesite="lax",
        max_age=15 * 60 # 15 minutes
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/api/v1/auth",
        max_age=7 * 24 * 60 * 60 # 7 days
    )

def get_auth_service(conn = Depends(get_db_connection)) -> AuthService:
    return AuthService(conn)

@router.post("/register", response_model=OrganizationRegistrationResponse, status_code=201)
async def register_organization(
    org_in: OrganizationCreate,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    ua_string = request.headers.get("user-agent", "Unknown")[:255]
    ip_address = request.client.host if request.client else "Unknown"

    result = await auth_service.register_organization(org_in, ua_string, ip_address)

    access_token = create_access_token(data={
        "user_id": result["user"]["id"],
        "email": result["user"]["email"],
        "role": result["user"]["role"],
        "organization_id": result["user"]["organization_id"],
        "session_id": result["session_id"]
    })

    set_auth_cookies(response, access_token, result["refresh_token"])

    return {
        "organization": result["organization"],
        "message": result["message"]
    }

@router.post("/login", response_model=SuccessResponse)
async def login(
    user_in: UserLogin,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    ua_string = request.headers.get("user-agent", "Unknown")[:255]
    ip_address = request.client.host if request.client else "Unknown"

    result = await auth_service.login(user_in, ua_string, ip_address)

    access_token = create_access_token(data={
        "user_id": result["user"]["id"],
        "email": result["user"]["email"],
        "role": result["user"]["role"],
        "organization_id": result["user"]["organization_id"],
        "session_id": result["session_id"]
    })

    set_auth_cookies(response, access_token, result["refresh_token"])

    return {"message": result["message"]}

@router.post("/refresh", response_model=SuccessResponse)
async def refresh_token(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    ua_string = request.headers.get("user-agent", "Unknown")[:255]
    ip_address = request.client.host if request.client else "Unknown"

    result = await auth_service.refresh_token(token, ua_string, ip_address)
    
    access_token = create_access_token(data={
        "user_id": result["user"]["id"],
        "email": result["user"]["email"],
        "role": result["user"]["role"],
        "organization_id": result["user"]["organization_id"],
        "session_id": result["session_id"]
    })
    
    set_auth_cookies(response, access_token, result["refresh_token"])

    return {"message": result["message"]}

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    user = await auth_service.get_me(current_user)
    return user

@router.post("/logout", response_model=SuccessResponse)
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    token = request.cookies.get("refresh_token")
    await auth_service.logout(token)

    response.delete_cookie(key="access_token", httponly=True, secure=False, samesite="lax")
    response.delete_cookie(key="refresh_token", httponly=True, secure=False, samesite="lax", path="/api/v1/auth")
    
    return {"message": "Logged out successfully"}

@router.get("/sessions", response_model=List[SessionResponse])
async def get_sessions(
    request: Request,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    current_token = request.cookies.get("refresh_token")
    sessions = await auth_service.get_sessions(current_token, current_user)
    return sessions

@router.delete("/sessions/other", response_model=SuccessResponse)
async def delete_other_sessions(
    request: Request,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    current_token = request.cookies.get("refresh_token")
    if not current_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
        
    await auth_service.delete_other_sessions(current_token, current_user)
    return {"message": "Other sessions revoked successfully"}

@router.get("/security-events", response_model=List[SecurityEventResponse])
async def get_security_events(
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    events = await auth_service.get_security_events(current_user)
    return events

@router.get("/password-policy", response_model=PasswordPolicy)
async def get_password_policy():
    return {
        "min_length": 8,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_number": True,
        "require_special": True
    }
