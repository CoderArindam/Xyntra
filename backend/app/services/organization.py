from fastapi import HTTPException, status
from app.database.connection import get_db_connection
from app.schemas.organization import OrganizationProfileResponse, OrganizationProfileUpdate

class OrganizationService:
    @staticmethod
    async def get_profile(org_id: int) -> OrganizationProfileResponse:
        async for conn in get_db_connection():
            row = await conn.fetchrow(
                "SELECT * FROM fn_get_organization_profile($1)",
                org_id
            )
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization profile not found"
                )
            return OrganizationProfileResponse(**dict(row))

    @staticmethod
    async def update_profile(org_id: int, updates: OrganizationProfileUpdate) -> OrganizationProfileResponse:
        async for conn in get_db_connection():
            update_data = updates.model_dump(exclude_unset=True)
            if not update_data:
                return await OrganizationService.get_profile(org_id)
            
            row = await conn.fetchrow(
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
