from fastapi import FastAPI
import warnings

# Silence pyannote's libtorchcodec warning traceback clutter
warnings.filterwarnings("ignore", category=UserWarning, module="pyannote.audio.core.io")
warnings.filterwarnings("ignore", message=".*torchcodec.*")
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from pathlib import Path
from app.database.connection import db
from app.routers import auth, boards, tasks, users, comments, attachments, activity, board_members, admin, invitations, notifications, my_work, preferences, organization, ai, task_proposals
from app.meeting.api import router as meeting_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.connect()
    yield
    # Shutdown — cancel all meeting sessions before stopping
    from app.meeting.api import meeting_service
    await meeting_service.shutdown_all()
    await db.disconnect()

app = FastAPI(
    title="KAIO API",
    description="Backend API for KAIO",
    version="1.0.0",
    lifespan=lifespan
)

# Ensure uploads directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

from app.config.settings import settings

origins = [origin.strip() for origin in settings.FRONTEND_ORIGINS.split(",") if origin.strip()]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(boards.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(comments.router, prefix="/api/v1")
app.include_router(attachments.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(activity.router, prefix="/api/v1")
app.include_router(board_members.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(invitations.router, prefix="/api/v1")
app.include_router(my_work.router, prefix="/api/v1")
app.include_router(preferences.router, prefix="/api/v1")
app.include_router(organization.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(task_proposals.router, prefix="/api/v1")
app.include_router(meeting_router, prefix="/api/v1")

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "KAIO API",
        "version": "1.0.0"
    }

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to KAIO API. Access /docs for API documentation."}
