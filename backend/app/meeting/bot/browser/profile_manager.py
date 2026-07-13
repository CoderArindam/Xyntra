"""Browser profile manager — owns profile directory lifecycle.

Responsibilities:
- Create profile directories
- Validate existing profiles
- File-based lock / unlock to prevent multi-process corruption
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.meeting.exceptions import ProfileLockError
from app.meeting.logger import get_logger

log = get_logger("browser.profile")

_LOCK_FILENAME = ".kaio_meeting.lock"


class ProfileManager:
    """Manages Playwright browser profile directories.

    A file-based lock prevents two bot instances from using the same
    profile simultaneously, which would corrupt cookies and tokens.
    """

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)

    # ------------------------------------------------------------------ #
    # Profile paths                                                        #
    # ------------------------------------------------------------------ #

    def get_profile_path(self, name: str = "default") -> Path:
        return self._base / name

    def ensure_exists(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        log.debug("Profile directory ready", path=str(path))

    def validate(self, path: Path) -> bool:
        """Return True if the profile directory looks healthy."""
        return path.exists() and path.is_dir()

    def clone_profile(self, src_name: str, dst_name: str) -> Path:
        """Clone an existing profile directory to a new location.
        Useful for reusing authenticated sessions across multiple bots.
        """
        import shutil
        src_path = self.get_profile_path(src_name)
        dst_path = self.get_profile_path(dst_name)
        
        if src_path.exists() and src_path.is_dir():
            try:
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                log.info("Profile cloned", src=src_name, dst=dst_name)
            except Exception as exc:
                log.warning("Profile clone failed, falling back to empty profile", src=src_name, dst=dst_name, error=str(exc))
                self.ensure_exists(dst_path)
        else:
            self.ensure_exists(dst_path)
            log.info("Profile clone skipped (src not found), created empty", src=src_name, dst=dst_name)
            
        return dst_path

    # ------------------------------------------------------------------ #
    # Locking                                                              #
    # ------------------------------------------------------------------ #

    def is_locked(self, path: Path) -> bool:
        lock_file = path / _LOCK_FILENAME
        if not lock_file.exists():
            return False
        try:
            data = json.loads(lock_file.read_text(encoding="utf-8"))
            pid = data.get("pid")
            if not isinstance(pid, int):
                return False
            # os.kill(pid, 0) raises OSError if the process does not exist.
            os.kill(pid, 0)
            return True
        except (OSError, ValueError, json.JSONDecodeError):
            # Stale lock — process is gone or file is corrupt.
            return False

    def lock(self, path: Path, session_id: str, profile_name: str) -> None:
        """Acquire profile lock. Raises ProfileLockError if already locked."""
        if self.is_locked(path):
            raise ProfileLockError(
                f"Browser profile at '{path}' is in use by another process. "
                "Stop the other bot session before starting a new one."
            )
        lock_file = path / _LOCK_FILENAME
        lock_data = {
            "pid": os.getpid(),
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "profile_name": profile_name
        }
        lock_file.write_text(json.dumps(lock_data), encoding="utf-8")
        log.debug("Profile locked", path=str(path), pid=os.getpid(), session_id=session_id)

    def unlock(self, path: Path, session_id: str) -> None:
        """Release profile lock only if owned by this session."""
        lock_file = path / _LOCK_FILENAME
        if lock_file.exists():
            try:
                data = json.loads(lock_file.read_text(encoding="utf-8"))
                pid = data.get("pid")
                lock_session_id = data.get("session_id")
                
                if pid == os.getpid() and lock_session_id == session_id:
                    lock_file.unlink(missing_ok=True)
                    log.debug("Profile unlocked", path=str(path), session_id=session_id)
                else:
                    log.warning(
                        "Profile unlock skipped (ownership mismatch)", 
                        path=str(path), 
                        expected_session=session_id,
                        actual_session=lock_session_id,
                        expected_pid=os.getpid(),
                        actual_pid=pid
                    )
            except (OSError, ValueError, json.JSONDecodeError):
                # Stale or corrupt lock file
                log.debug("Profile unlocked (stale lock removed)", path=str(path))

    async def remove_when_available(self, path: Path, session_id: str) -> None:
        """Retry-safe deletion of the profile directory. Best effort."""
        if not path.exists():
            return
            
        import shutil
        import asyncio
        
        max_attempts = 10
        delay = 0.5
        
        for attempt in range(1, max_attempts + 1):
            try:
                shutil.rmtree(path, ignore_errors=False)
                log.info("meeting.profile.delete_success", session_id=session_id, profile_path=str(path))
                return
            except Exception as exc:
                log.debug(
                    "meeting.profile.delete_retry",
                    session_id=session_id,
                    profile_path=str(path),
                    attempt=attempt,
                    error=str(exc)
                )
                if attempt < max_attempts:
                    await asyncio.sleep(delay)
                else:
                    log.warning(
                        "meeting.profile.delete_failed",
                        session_id=session_id,
                        profile_path=str(path),
                        error=str(exc)
                    )
