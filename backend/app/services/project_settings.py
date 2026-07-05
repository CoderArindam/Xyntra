import asyncpg
from typing import Optional
from fastapi import HTTPException
from app.schemas.board import ProjectSettingsResponse, ProjectSettingsUpdate, CanonicalBoardResponse, ProjectStatistics

class ProjectSettingsService:
    @staticmethod
    async def get_settings(conn: asyncpg.Connection, board_id: int) -> ProjectSettingsResponse:
        board_row = await conn.fetchrow("SELECT * FROM fn_get_project_settings($1)", board_id)
        if not board_row:
            raise HTTPException(status_code=404, detail="Project not found")
        
        stats_row = await conn.fetchrow("SELECT * FROM fn_get_project_statistics($1)", board_id)
        
        return ProjectSettingsResponse(
            settings=CanonicalBoardResponse(**dict(board_row)),
            statistics=ProjectStatistics(**dict(stats_row)) if stats_row else ProjectStatistics(
                total_tasks=0, completed_tasks=0, overdue_tasks=0, members_count=0, columns_count=0, last_activity=None
            )
        )

    @staticmethod
    async def update_settings(conn: asyncpg.Connection, board_id: int, updates: ProjectSettingsUpdate) -> ProjectSettingsResponse:
        row = await conn.fetchrow(
            """
            SELECT * FROM fn_update_project_settings(
                $1, $2, $3, $4, $5, $6, $7, $8
            )
            """,
            board_id,
            updates.name,
            updates.description,
            updates.icon,
            updates.color,
            updates.cover_gradient,
            updates.default_assignee_id if updates.default_assignee_id is not None else -1,
            updates.project_lead_id if updates.project_lead_id is not None else -1
        )
        if not row:
            raise HTTPException(status_code=404, detail="Project not found or update failed")
            
        stats_row = await conn.fetchrow("SELECT * FROM fn_get_project_statistics($1)", board_id)
        return ProjectSettingsResponse(
            settings=CanonicalBoardResponse(**dict(row)),
            statistics=ProjectStatistics(**dict(stats_row)) if stats_row else ProjectStatistics(
                total_tasks=0, completed_tasks=0, overdue_tasks=0, members_count=0, columns_count=0, last_activity=None
            )
        )

    @staticmethod
    async def archive_project(conn: asyncpg.Connection, board_id: int) -> ProjectSettingsResponse:
        row = await conn.fetchrow("SELECT * FROM fn_archive_project($1)", board_id)
        if not row:
            raise HTTPException(status_code=404, detail="Project not found or already archived")
            
        stats_row = await conn.fetchrow("SELECT * FROM fn_get_project_statistics($1)", board_id)
        return ProjectSettingsResponse(
            settings=CanonicalBoardResponse(**dict(row)),
            statistics=ProjectStatistics(**dict(stats_row)) if stats_row else ProjectStatistics(
                total_tasks=0, completed_tasks=0, overdue_tasks=0, members_count=0, columns_count=0, last_activity=None
            )
        )
