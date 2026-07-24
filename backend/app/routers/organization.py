from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from app.schemas.organization import OrganizationProfileResponse, OrganizationProfileUpdate
from app.services.organization_service import OrganizationService
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection

router = APIRouter(prefix="/organization", tags=["Organization"])


def get_org_service(conn = Depends(get_db_connection)) -> OrganizationService:
    return OrganizationService(conn)

@router.get("/profile", response_model=OrganizationProfileResponse)
async def get_organization_profile(
    current_user: dict = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization context found")
    return await org_service.get_profile(org_id)

@router.patch("/profile", response_model=OrganizationProfileResponse)
async def update_organization_profile(
    updates: OrganizationProfileUpdate,
    current_user: dict = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    if current_user.get("role") != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admins can modify organization profile"
        )
    
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization context found")
        
    return await org_service.update_profile(org_id, updates)

@router.post("/logo")
async def upload_organization_logo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    if current_user.get("role") != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admins can modify organization profile"
        )
    
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization context found")
        
    url = await org_service.upload_logo(file, org_id)
    return {"logo_url": url}
