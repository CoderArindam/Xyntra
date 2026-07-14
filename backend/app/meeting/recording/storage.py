"""Recording storage abstraction for the meeting module.

All recording persistence goes through RecordingStorage.
This allows future cloud-storage providers (S3, GCS) to be swapped
in without changing any recorder logic.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from app.meeting.logger import get_logger

log = get_logger("recording.storage")


class RecordingStorage(ABC):
    """Abstract base for recording persistence backends."""

    @abstractmethod
    async def save(self, session_id: str, data: bytes, fmt: str) -> tuple[str, str]:
        """Persist recording bytes.

        Returns:
            (local_path, storage_uri) — local_path is the on-disk path;
            storage_uri is the abstract identifier (file:// now, s3:// later).
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, uri: str) -> None:
        """Remove a recording by URI. Silently ignores missing files."""
        raise NotImplementedError


class LocalRecordingStorage(RecordingStorage):
    """Persists recordings to the local filesystem.

    Directory layout::
        {root}/{session_id}/{timestamp}_{uuid}.{fmt}

    Writes are atomic: data is written to a .tmp file first, then
    renamed to the final filename, preventing partial reads.
    """

    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()

    async def save(self, session_id: str, data: bytes, fmt: str) -> tuple[str, str]:
        """Write recording data atomically. Returns (local_path, storage_uri)."""
        session_dir = self._root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        uid = uuid.uuid4().hex[:8]
        filename = f"{ts}_{uid}.{fmt}"
        final_path = session_dir / filename
        tmp_path = final_path.with_suffix(f".{fmt}.tmp")

        try:
            tmp_path.write_bytes(data)
            tmp_path.rename(final_path)
        except OSError as exc:
            # Clean up tmp if rename fails
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise exc

        storage_uri = final_path.as_uri()  # file:///...
        log.info(
            "recording.storage.saved",
            session_id=session_id,
            path=str(final_path),
            uri=storage_uri,
            size_bytes=len(data),
        )
        return str(final_path), storage_uri

    async def delete(self, uri: str) -> None:
        """Remove a file:// URI. Silently ignores missing files."""
        if not uri.startswith("file://"):
            log.warning("recording.storage.delete_skipped_non_local", uri=uri)
            return
        path = Path(uri.removeprefix("file://"))
        try:
            path.unlink(missing_ok=True)
            log.info("recording.storage.deleted", path=str(path))
        except OSError as exc:
            log.warning("recording.storage.delete_failed", path=str(path), error=str(exc))


def compute_sha256(data: bytes) -> str:
    """Return the hex-encoded SHA-256 checksum of the given bytes."""
    return hashlib.sha256(data).hexdigest()
