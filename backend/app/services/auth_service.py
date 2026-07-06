import json
import logging
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional
import asyncpg
from fastapi import HTTPException

from app.schemas.auth import OrganizationCreate, UserLogin
from app.auth.password import get_password_hash, verify_password

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    def parse_user_agent(self, ua_string: str) -> Tuple[str, str, str]:
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

    async def create_session(self, user_id: int, ua_string: str, ip_address: str) -> Tuple[str, int]:
        refresh_token = secrets.token_urlsafe(64)
        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        browser, platform, device_name = self.parse_user_agent(ua_string)
        
        session_id = await self.conn.fetchval(
            """
            INSERT INTO user_sessions (user_id, refresh_token_hash, browser, platform, device_name, ip_address, expires_at, last_active_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP)
            RETURNING id
            """,
            user_id, refresh_token_hash, browser, platform, device_name, ip_address, expires_at
        )
        return refresh_token, session_id

    async def register_organization(self, org_in: OrganizationCreate, ua_string: str, ip_address: str) -> dict:
        hashed_password = get_password_hash(org_in.password)
        try:
            result = await self.conn.fetchval(
                "SELECT create_organization_with_admin($1, $2, $3, $4, $5)",
                org_in.org_name,
                org_in.email,
                hashed_password,
                org_in.first_name,
                org_in.last_name
            )
            if not result:
                raise HTTPException(status_code=500, detail="Failed to create organization")

            user_row = await self.conn.fetchrow(
                "SELECT id, email, role, organization_id FROM users WHERE email = $1",
                org_in.email
            )

            refresh_token, session_id = await self.create_session(user_row["id"], ua_string, ip_address)
            
            return {
                "organization": {"id": result, "name": org_in.org_name, "created_at": datetime.now(timezone.utc)},
                "user": dict(user_row),
                "refresh_token": refresh_token,
                "session_id": session_id,
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

    async def login(self, user_in: UserLogin, ua_string: str, ip_address: str) -> dict:
        user_row = await self.conn.fetchrow(
            "SELECT id, email, password_hash, role, organization_id FROM users WHERE email = $1 AND deleted_at IS NULL",
            user_in.email
        )

        if not user_row or not verify_password(user_in.password, user_row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        refresh_token, session_id = await self.create_session(user_row["id"], ua_string, ip_address)
        browser, platform, _ = self.parse_user_agent(ua_string)

        await self.conn.execute(
            """
            INSERT INTO audit_logs (organization_id, user_id, action, entity_type, entity_id, ip_address, details)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            user_row["organization_id"], user_row["id"], "LOGIN", "USER", user_row["id"], ip_address, json.dumps({"browser": browser, "platform": platform, "status": "Success"})
        )

        return {
            "user": dict(user_row),
            "refresh_token": refresh_token,
            "session_id": session_id,
            "message": "Login successful"
        }

    async def refresh_token(self, token: str, ua_string: str, ip_address: str) -> dict:
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        session_row = await self.conn.fetchrow(
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
            if session_row["revoked_at"]:
                await self.conn.execute("UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE user_id = $1", session_row["user_id"])
            raise HTTPException(status_code=401, detail="Session expired or revoked")

        user_row = await self.conn.fetchrow(
            "SELECT id, email, role, organization_id FROM users WHERE id = $1 AND deleted_at IS NULL",
            session_row["user_id"]
        )
        if not user_row:
            raise HTTPException(status_code=401, detail="User not found")

        await self.conn.execute("UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE id = $1", session_row["id"])
        
        new_refresh_token, new_session_id = await self.create_session(user_row["id"], ua_string, ip_address)
        
        return {
            "user": dict(user_row),
            "refresh_token": new_refresh_token,
            "session_id": new_session_id,
            "message": "Token refreshed"
        }

    async def get_me(self, current_user: dict) -> dict:
        user_row = await self.conn.fetchrow(
            "SELECT id, email, first_name, last_name, avatar_url, role, organization_id, is_email_verified FROM users WHERE id = $1 AND deleted_at IS NULL",
            current_user["id"]
        )
        if not user_row:
            raise HTTPException(status_code=404, detail="User not found")
        return dict(user_row)

    async def logout(self, token: Optional[str]):
        if token:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            await self.conn.execute(
                "UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE refresh_token_hash = $1",
                token_hash
            )

    async def get_sessions(self, current_token: Optional[str], current_user: dict) -> List[dict]:
        current_token_hash = hashlib.sha256(current_token.encode()).hexdigest() if current_token else ""

        rows = await self.conn.fetch(
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

    async def delete_other_sessions(self, current_token: str, current_user: dict):
        current_token_hash = hashlib.sha256(current_token.encode()).hexdigest()

        await self.conn.execute(
            """
            UPDATE user_sessions 
            SET revoked_at = CURRENT_TIMESTAMP 
            WHERE user_id = $1 AND refresh_token_hash != $2 AND revoked_at IS NULL
            """,
            current_user["id"], current_token_hash
        )

    async def get_security_events(self, current_user: dict) -> List[dict]:
        rows = await self.conn.fetch(
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