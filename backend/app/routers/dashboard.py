import logging
from fastapi import APIRouter, Depends

from app.auth.dependencies import require_proposal_review_access
from app.database.connection import get_db_connection
from app.schemas.dashboard import DashboardSummaryResponse
from app.schemas.envelope import DataEnvelope
from app.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard"])

def get_dashboard_service(conn = Depends(get_db_connection)) -> DashboardService:
    return DashboardService(conn)

@router.get("/dashboard/summary", response_model=DataEnvelope[DashboardSummaryResponse])
async def get_dashboard_summary(
    current_user: dict = Depends(require_proposal_review_access),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """Returns aggregated organization metrics, per-board summary grid, and recent activity history.

    Requires Manager or Superadmin role in the active organization.
    """
    summary = await dashboard_service.get_dashboard_summary(current_user)
    return DataEnvelope(data=summary)
