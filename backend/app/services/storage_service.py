import os
import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile

UPLOAD_DIR = Path("uploads/avatars")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

LOGO_DIR = Path("uploads/logos")
LOGO_DIR.mkdir(parents=True, exist_ok=True)

class StorageService:
    @staticmethod
    async def save_avatar(file: UploadFile) -> str:
        """
        Saves an uploaded avatar locally and returns the public URL path.
        """
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename

        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # The public URL will be served from /uploads
        return f"/uploads/avatars/{unique_filename}"

    @staticmethod
    async def save_logo(file: UploadFile) -> str:
        """
        Saves an uploaded workspace logo locally and returns the public URL path.
        """
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = LOGO_DIR / unique_filename

        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return f"/uploads/logos/{unique_filename}"
