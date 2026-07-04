import json
import logging
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Response, Request
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
from app.auth.password import get_password_hash, verify_password
from app.auth.jwt import create_access_token
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection

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


def parse_user_agent(ua_string: str):
    ua = ua_string.lower()
    browser = "Unknown"
    if "chrome" in ua and "edg" not in ua:
        browser = "Chrome"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "edg" in ua:
        browser = "Edge"
    
    platform = "Unknown"
    if "windows" in ua:
        platform = "Windows"
    elif "mac" in ua:
        platform = "macOS"
    elif "linux" in ua:
        platform = "Linux"
    elif "android" in ua:
        platform = "Android"
    elif "iphone" in ua or "ipad" in ua:
        platform = "iOS"
        
    return browser, platform, f"{browser} on {platform}"

async def create_session(conn: asyncpg.Connection, user_id: int, request: Request):
    refresh_token = secrets.token_urlsafe(64)
    refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    ua_string = request.headers.get("user-agent", "Unknown")[:255]
    browser, platform, device_name = parse_user_agent(ua_string)
    ip_address = request.client.host if request.client else "Unknown"
    
    session_id = await conn.fetchval(
        """
        INSERT INTO user_sessions (user_id, refresh_token_hash, browser, platform, device_name, ip_address, expires_at, last_active_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP)
        RETURNING id
        """,
        user_id, refresh_token_hash, browser, platform, device_name, ip_address, expires_at
    )
    return refresh_token, session_id


@router.post("/register", response_model=OrganizationRegistrationResponse, status_code=201)
async def register_organization(
    org_in: OrganizationCreate,
    request: Request,
    response: Response,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    hashed_password = get_password_hash(org_in.password)
    try:
        result = await conn.fetchval(
            "SELECT create_organization_with_admin($1, $2, $3, $4, $5)",
            org_in.org_name,
            org_in.email,
            hashed_password,
            org_in.first_name,
            org_in.last_name
        )
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create organization")

        # After create_organization_with_admin returns org_id, we need user info
        user_row = await conn.fetchrow(
            "SELECT id, email, role, organization_id FROM users WHERE email = $1",
            org_in.email
        )

        refresh_token, session_id = await create_session(conn, user_row["id"], request)

        access_token = create_access_token(data={
            "user_id": user_row["id"],
            "email": user_row["email"],
            "role": user_row["role"],
            "organization_id": user_row["organization_id"],
            "session_id": session_id
        })

        set_auth_cookies(response, access_token, refresh_token)

        return {
            "organization": {"id": result, "name": org_in.org_name, "created_at": datetime.now(timezone.utc)},
            "message": "Registration successful"
        }
    except asyncpg.exceptions.RaiseError as e:
        if "already registered" in str(e) or "unique constraint" in str(e).lower():
            raise HTTPException(status_code=400, detail="Email already registered")
        logger.error(f"PostgreSQL RaiseError in register_organization: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in register_organization: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.post("/login", response_model=SuccessResponse)
async def login(
    user_in: UserLogin,
    request: Request,
    response: Response,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    user_row = await conn.fetchrow(
        "SELECT id, email, password_hash, role, organization_id FROM users WHERE email = $1 AND deleted_at IS NULL",
        user_in.email
    )

    if not user_row or not verify_password(user_in.password, user_row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    refresh_token, session_id = await create_session(conn, user_row["id"], request)

    access_token = create_access_token(data={
        "user_id": user_row["id"],
        "email": user_row["email"],
        "role": user_row["role"],
        "organization_id": user_row["organization_id"],
        "session_id": session_id
    })

    set_auth_cookies(response, access_token, refresh_token)

    ua_string = request.headers.get("user-agent", "Unknown")[:255]
    browser, platform, _ = parse_user_agent(ua_string)
    ip_address = request.client.host if request.client else "Unknown"
    
    await conn.execute(
        """
        INSERT INTO audit_logs (organization_id, user_id, action, entity_type, entity_id, ip_address, details)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        user_row["organization_id"], user_row["id"], "LOGIN", "USER", user_row["id"], ip_address, json.dumps({"browser": browser, "platform": platform, "status": "Success"})
    )

    return {"message": "Login successful"}


@router.post("/refresh", response_model=SuccessResponse)
async def refresh_token(
    request: Request,
    response: Response,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Find the session
    session_row = await conn.fetchrow(
        """
        SELECT id, user_id, revoked_at, expires_at 
        FROM user_sessions 
        WHERE refresh_token_hash = $1
        """,
        token_hash
    )

    if not session_row:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if session_row["revoked_at"] or session_row["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        # Token theft protection: if it's already revoked, revoke all sessions for this user
        if session_row["revoked_at"]:
            await conn.execute("UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE user_id = $1", session_row["user_id"])
        raise HTTPException(status_code=401, detail="Session expired or revoked")

    # Fetch user
    user_row = await conn.fetchrow(
        "SELECT id, email, role, organization_id FROM users WHERE id = $1 AND deleted_at IS NULL",
        session_row["user_id"]
    )
    if not user_row:
        raise HTTPException(status_code=401, detail="User not found")

    # Rotate tokens: Revoke old session, create new
    await conn.execute("UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE id = $1", session_row["id"])
    
    new_refresh_token, new_session_id = await create_session(conn, user_row["id"], request)
    
    access_token = create_access_token(data={
        "user_id": user_row["id"],
        "email": user_row["email"],
        "role": user_row["role"],
        "organization_id": user_row["organization_id"],
        "session_id": new_session_id
    })
    
    set_auth_cookies(response, access_token, new_refresh_token)

    return {"message": "Token refreshed"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Returns the currently authenticated user's canonical information.
    """
    user_row = await conn.fetchrow(
        "SELECT id, email, first_name, last_name, avatar_url, role, organization_id, is_email_verified FROM users WHERE id = $1 AND deleted_at IS NULL",
        current_user["id"]
    )
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")
        
    return dict(user_row)


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    request: Request,
    response: Response,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    token = request.cookies.get("refresh_token")
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        await conn.execute(
            "UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE refresh_token_hash = $1",
            token_hash
        )

    response.delete_cookie(key="access_token", httponly=True, secure=False, samesite="lax")
    response.delete_cookie(key="refresh_token", httponly=True, secure=False, samesite="lax", path="/api/v1/auth")
    
    return {"message": "Logged out successfully"}

from typing import List

@router.get("/sessions", response_model=List[SessionResponse])
async def get_sessions(
    request: Request,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    current_token = request.cookies.get("refresh_token")
    current_token_hash = hashlib.sha256(current_token.encode()).hexdigest() if current_token else ""

    rows = await conn.fetch(
        """
        SELECT id, browser, platform, device_name, ip_address, last_active_at, created_at, refresh_token_hash
        FROM user_sessions
        WHERE user_id = $1 AND revoked_at IS NULL AND expires_at > CURRENT_TIMESTAMP
        ORDER BY last_active_at DESC NULLS LAST
        """,
        current_user["id"]
    )
    
    sessions = []
    for row in rows:
        session_dict = dict(row)
        session_dict["is_current"] = (row["refresh_token_hash"] == current_token_hash)
        sessions.append(session_dict)
        
    return sessions

@router.delete("/sessions/other", response_model=SuccessResponse)
async def delete_other_sessions(
    request: Request,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    current_token = request.cookies.get("refresh_token")
    if not current_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
        
    current_token_hash = hashlib.sha256(current_token.encode()).hexdigest()

    await conn.execute(
        """
        UPDATE user_sessions 
        SET revoked_at = CURRENT_TIMESTAMP 
        WHERE user_id = $1 AND refresh_token_hash != $2 AND revoked_at IS NULL
        """,
        current_user["id"], current_token_hash
    )
    
    return {"message": "Other sessions revoked successfully"}

@router.get("/security-events", response_model=List[SecurityEventResponse])
async def get_security_events(
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    rows = await conn.fetch(
        """
        SELECT id, action, ip_address, details, created_at
        FROM audit_logs
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 50
        """,
        current_user["id"]
    )
    
    events = []
    for row in rows:
        event = dict(row)
        if isinstance(event.get("details"), str):
            try:
                event["details"] = json.loads(event["details"])
            except:
                event["details"] = {}
        events.append(event)
        
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
