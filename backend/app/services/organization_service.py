from fastapi import HTTPException, status, UploadFile
import asyncpg
from app.schemas.organization import OrganizationProfileResponse, OrganizationProfileUpdate
from app.services.storage_service import StorageService

class OrganizationService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_profile(self, org_id: int) -> OrganizationProfileResponse:
        row = await self.conn.fetchrow(
            "SELECT * FROM fn_get_organization_profile($1)",
            org_id
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization profile not found"
            )
        return OrganizationProfileResponse(**dict(row))

    async def update_profile(self, org_id: int, updates: OrganizationProfileUpdate) -> OrganizationProfileResponse:
        update_data = updates.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_profile(org_id)
        
        row = await self.conn.fetchrow(
            """
            SELECT * FROM fn_update_organization_profile(
                $1,
                p_name := $2,
                p_logo_url := $3,
                p_website := $4,
                p_description := $5,
                p_industry := $6,
                p_company_size := $7
            )
            """,
            org_id,
            update_data.get('name'),
            update_data.get('logo_url'),
            update_data.get('website'),
            update_data.get('description'),
            update_data.get('industry'),
            update_data.get('company_size')
        )
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or update failed"
            )
        return OrganizationProfileResponse(**dict(row))

    async def upload_logo(self, file: UploadFile, org_id: int) -> str:
        try:
            url = await StorageService.save_logo(file)
            # You might want to update the profile directly, or leave it to the user.
            # But the router was just returning the URL.
            return url
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to upload logo")