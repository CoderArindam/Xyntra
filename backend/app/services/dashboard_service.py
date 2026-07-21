import logging
import asyncpg
from fastapi import HTTPException

from app.schemas.dashboard import (
    DashboardSummaryResponse,
    DashboardKPIs,
    DashboardTasksByStatus,
    DashboardBoardSummary
)
from app.schemas.activity import CanonicalActivityResponse

logger = logging.getLogger(__name__)

class DashboardService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_dashboard_summary(self, current_user: dict) -> DashboardSummaryResponse:
        try:
            org_id = current_user.get("organization_id")
            if not org_id:
                raise HTTPException(status_code=400, detail="Organization context missing")

            # 1. Fetch Org KPIs (Single query to v_dashboard_kpis_canonical)
            kpi_row = await self.conn.fetchrow(
                """
                SELECT * FROM v_dashboard_kpis_canonical
                WHERE organization_id = $1
                """,
                org_id
            )

            if kpi_row:
                kpis = DashboardKPIs(
                    total_tasks=kpi_row["total_tasks"],
                    tasks_by_status=DashboardTasksByStatus(
                        todo=kpi_row["todo_tasks"],
                        in_progress=kpi_row["in_progress_tasks"],
                        review=kpi_row["review_tasks"],
                        done=kpi_row["done_tasks"]
                    ),
                    overdue_tasks=kpi_row["overdue_tasks"],
                    total_boards=kpi_row["total_boards"],
                    team_size=kpi_row["total_team_members"],
                    pending_proposals_count=kpi_row["pending_proposals_count"],
                    active_meetings_count=kpi_row["active_meetings_count"]
                )
            else:
                kpis = DashboardKPIs(
                    total_tasks=0,
                    tasks_by_status=DashboardTasksByStatus(todo=0, in_progress=0, review=0, done=0),
                    overdue_tasks=0,
                    total_boards=0,
                    team_size=0,
                    pending_proposals_count=0,
                    active_meetings_count=0
                )

            # 2. Fetch Per-Board Summaries (Single query to v_dashboard_board_summaries_canonical)
            board_rows = await self.conn.fetch(
                """
                SELECT * FROM v_dashboard_board_summaries_canonical
                WHERE organization_id = $1
                ORDER BY name ASC
                """,
                org_id
            )
            boards = [DashboardBoardSummary(**dict(r)) for r in board_rows]

            # 3. Fetch Recent Activity Slice (Single query to v_activities_canonical, last 10 rows)
            activity_rows = await self.conn.fetch(
                """
                SELECT * FROM v_activities_canonical
                WHERE organization_id = $1
                ORDER BY created_at DESC, id DESC
                LIMIT 10
                """,
                org_id
            )
            recent_activity = [CanonicalActivityResponse(**dict(r)) for r in activity_rows]

            return DashboardSummaryResponse(
                kpis=kpis,
                boards=boards,
                recent_activity=recent_activity
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching dashboard summary: {e}")
            raise HTTPException(status_code=400, detail="An unexpected error occurred while generating dashboard summary")
