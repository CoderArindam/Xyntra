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
        if "edg" in ua or "edge" in ua:
            browser = "Edge"
        elif "chrome" in ua or "crios" in ua:
            browser = "Chrome"
        elif "firefox" in ua or "fxios" in ua:
            browser = "Firefox"
        elif "safari" in ua:
            browser = "Safari"
        elif "opera" in ua or "opr" in ua:
            browser = "Opera"
        
        platform = "Unknown"
        if "windows" in ua:
            platform = "Windows"
        elif "macintosh" in ua or "mac os" in ua:
            platform = "macOS"
        elif "android" in ua:
            platform = "Android"
        elif "iphone" in ua or "ipad" in ua or "ipod" in ua:
            platform = "iOS"
        elif "linux" in ua:
            platform = "Linux"
            
        return browser, platform, f"{browser} on {platform}"

    async def create_session(self, user_id: int, ua_string: str, ip_address: str) -> Tuple[str, int]:
        refresh_token = secrets.token_urlsafe(64)
        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        browser, platform, device_name = self.parse_user_agent(ua_string)
        
        session_id = await self.conn.fetchval(
            "SELECT fn_create_user_session($1, $2, $3, $4, $5, $6, $7)",
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
                "SELECT id, email, role, organization_id FROM v_users_canonical WHERE email = $1",
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
        except asyncpg.exceptions.UniqueViolationError:
            raise HTTPException(status_code=409, detail="This email is already registered")
        except asyncpg.exceptions.RaiseError as e:
            if "already registered" in str(e).lower() or "unique constraint" in str(e).lower() or "unique_idx" in str(e).lower():
                raise HTTPException(status_code=409, detail="This email is already registered")
            logger.error(f"PostgreSQL RaiseError in register_organization: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error in register_organization: {e}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred")

    async def login(self, user_in: UserLogin, ua_string: str, ip_address: str) -> dict:
        user_row = await self.conn.fetchrow(
            "SELECT id, email, password_hash, role, organization_id FROM v_users_canonical WHERE email = $1",
            user_in.email
        )

        browser, platform, _ = self.parse_user_agent(ua_string)

        if not user_row or not verify_password(user_in.password, user_row["password_hash"]):
            if user_row:
                await self.conn.execute(
                    "SELECT fn_log_security_event($1, $2, $3, $4::entity_type_enum, $5, $6, $7::jsonb)",
                    user_row["organization_id"], user_row["id"], "FAILED_LOGIN", "USER", user_row["id"], ip_address, json.dumps({"browser": browser, "platform": platform, "status": "Failed", "reason": "Invalid credentials"})
                )
            raise HTTPException(status_code=401, detail="Invalid email or password")

        is_new_device = await self.conn.fetchval(
            "SELECT fn_check_is_new_device($1, $2, $3)",
            user_row["id"], browser, platform
        )

        refresh_token, session_id = await self.create_session(user_row["id"], ua_string, ip_address)

        action = "NEW_DEVICE_LOGIN" if is_new_device else "LOGIN"
        details = {
            "browser": browser,
            "platform": platform,
            "status": "Success",
            "is_new_device": bool(is_new_device)
        }

        await self.conn.execute(
            "SELECT fn_log_security_event($1, $2, $3, $4::entity_type_enum, $5, $6, $7::jsonb)",
            user_row["organization_id"], user_row["id"], action, "USER", user_row["id"], ip_address, json.dumps(details)
        )

        return {
            "user": dict(user_row),
            "refresh_token": refresh_token,
            "session_id": session_id,
            "message": "Login successful"
        }

    async def refresh_token(self, token: str, ua_string: str, ip_address: str) -> dict:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        new_refresh_token = secrets.token_urlsafe(64)
        new_token_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        browser, platform, _ = self.parse_user_agent(ua_string)

        row = await self.conn.fetchrow(
            "SELECT session_id, user_id FROM fn_refresh_user_session($1, $2, $3, $4, $5, $6)",
            token_hash, new_token_hash, expires_at, browser, platform, ip_address
        )

        if not row or not row["session_id"]:
            raise HTTPException(status_code=401, detail="Session expired or revoked")

        user_row = await self.conn.fetchrow(
            "SELECT id, email, role, organization_id FROM v_users_canonical WHERE id = $1",
            row["user_id"]
        )
        if not user_row:
            raise HTTPException(status_code=401, detail="User not found")

        return {
            "user": dict(user_row),
            "refresh_token": new_refresh_token,
            "session_id": row["session_id"],
            "message": "Token refreshed"
        }

    async def get_me(self, current_user: dict) -> dict:
        user_row = await self.conn.fetchrow(
            "SELECT id, email, first_name, last_name, avatar_url, role, organization_id, is_email_verified FROM v_users_canonical WHERE id = $1",
            current_user["id"]
        )
        if not user_row:
            raise HTTPException(status_code=404, detail="User not found")
        return dict(user_row)

    async def logout(self, token: Optional[str]):
        if token:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            await self.conn.execute(
                "SELECT fn_revoke_session_by_token_hash($1)",
                token_hash
            )

    async def get_sessions(self, current_token: Optional[str], current_user: dict) -> List[dict]:
        current_token_hash = hashlib.sha256(current_token.encode()).hexdigest() if current_token else ""
        current_session_id = current_user.get("session_id")

        rows = await self.conn.fetch(
            "SELECT id, browser, platform, device_name, ip_address, last_active_at, created_at, refresh_token_hash FROM fn_get_user_sessions($1)",
            current_user["id"]
        )
        
        sessions = []
        for row in rows:
            session_dict = dict(row)
            session_dict["is_current"] = (
                (current_session_id is not None and row["id"] == current_session_id) or
                (bool(current_token_hash) and row["refresh_token_hash"] == current_token_hash)
            )
            sessions.append(session_dict)
            
        return sessions

    async def delete_other_sessions(self, current_user: dict, current_token: Optional[str] = None, ua_string: str = "Unknown", ip_address: str = "Unknown"):
        current_session_id = current_user.get("session_id")
        current_token_hash = hashlib.sha256(current_token.encode()).hexdigest() if current_token else None

        await self.conn.execute(
            "SELECT fn_revoke_other_user_sessions($1, $2, $3)",
            current_user["id"], current_session_id, current_token_hash
        )

        org_id = current_user.get("organization_id")
        if not org_id:
            org_id = await self.conn.fetchval(
                "SELECT organization_id FROM v_users_canonical WHERE id = $1",
                current_user["id"]
            )

        browser, platform, _ = self.parse_user_agent(ua_string)
        await self.conn.execute(
            "SELECT fn_log_security_event($1, $2, $3, $4::entity_type_enum, $5, $6, $7::jsonb)",
            org_id,
            current_user["id"],
            "REVOKED_OTHER_SESSIONS",
            "USER",
            current_user["id"],
            ip_address,
            json.dumps({"browser": browser, "platform": platform, "status": "Success"})
        )

    async def get_security_events(self, current_user: dict) -> List[dict]:
        rows = await self.conn.fetch(
            "SELECT id, action, ip_address, details, created_at FROM fn_get_user_security_events($1, 50)",
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