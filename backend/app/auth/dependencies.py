from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from app.auth.jwt import verify_token
import asyncpg
from app.database.connection import get_db_connection

# We keep this for API documentation purposes, but don't strictly require it
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

async def get_current_user(
    request: Request, 
    token: str = Depends(oauth2_scheme),
    conn: asyncpg.Connection = Depends(get_db_connection)
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    
    # Prioritize cookie token, fallback to Authorization header
    cookie_token = request.cookies.get("access_token")
    actual_token = cookie_token or token
    
    if not actual_token:
        raise credentials_exception

    payload = verify_token(actual_token)
    if payload is None:
        raise credentials_exception

    user_id: int = payload.get("user_id")
    email: str = payload.get("email")
    role: str = payload.get("role", "MEMBER")
    organization_id: int = payload.get("organization_id")
    session_id: int = payload.get("session_id")

    if user_id is None or email is None:
        raise credentials_exception

    # Immediately reject if the session is revoked
    if session_id:
        revoked_at = await conn.fetchval(
            "SELECT revoked_at FROM user_sessions WHERE id = $1", 
            session_id
        )
        if revoked_at is not None:
            raise credentials_exception

    return {
        "id": user_id,
        "email": email,
        "role": role,
        "organization_id": organization_id,
        "session_id": session_id,
    }
