from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from app.schemas.organization import OrganizationProfileResponse, OrganizationProfileUpdate
from app.services.organization import OrganizationService
from app.services.storage_service import StorageService
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/organization", tags=["Organization"])

@router.get("/profile", response_model=OrganizationProfileResponse)
async def get_organization_profile(current_user: dict = Depends(get_current_user)):
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization context found")
    return await OrganizationService.get_profile(org_id)

@router.patch("/profile", response_model=OrganizationProfileResponse)
async def update_organization_profile(
    updates: OrganizationProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("role") != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admins can modify organization profile"
        )
    
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization context found")
        
    return await OrganizationService.update_profile(org_id, updates)

@router.post("/logo")
async def upload_organization_logo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("role") != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admins can modify organization profile"
        )
    
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization context found")
        
    try:
        url = await StorageService.save_logo(file)
        return {"logo_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upload logo")
