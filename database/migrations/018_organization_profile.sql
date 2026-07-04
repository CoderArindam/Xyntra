-- 018_organization_profile.sql
-- Add profile fields to organizations

ALTER TABLE organizations ADD COLUMN IF NOT EXISTS logo_url VARCHAR(1024);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS website VARCHAR(255);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS industry VARCHAR(100);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS company_size VARCHAR(50);

-- Function to get organization profile with stats
CREATE OR REPLACE FUNCTION fn_get_organization_profile(p_org_id INTEGER)
RETURNS TABLE (
    id INTEGER,
    name VARCHAR(255),
    logo_url VARCHAR(1024),
    website VARCHAR(255),
    description TEXT,
    industry VARCHAR(100),
    company_size VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE,
    owner_name VARCHAR(255),
    owner_email VARCHAR(255),
    members_count BIGINT,
    projects_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        o.id,
        o.name,
        o.logo_url,
        o.website,
        o.description,
        o.industry,
        o.company_size,
        o.created_at,
        (SELECT CONCAT_WS(' ', u.first_name, u.last_name)::VARCHAR FROM users u WHERE u.organization_id = o.id AND u.role = 'SUPER_ADMIN' AND u.deleted_at IS NULL ORDER BY u.created_at ASC LIMIT 1) as owner_name,
        (SELECT u.email::VARCHAR FROM users u WHERE u.organization_id = o.id AND u.role = 'SUPER_ADMIN' AND u.deleted_at IS NULL ORDER BY u.created_at ASC LIMIT 1) as owner_email,
        (SELECT COUNT(*) FROM users u WHERE u.organization_id = o.id AND u.deleted_at IS NULL) as members_count,
        (SELECT COUNT(*) FROM boards b WHERE b.organization_id = o.id AND b.deleted_at IS NULL) as projects_count
    FROM organizations o
    WHERE o.id = p_org_id AND o.deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to update organization profile
CREATE OR REPLACE FUNCTION fn_update_organization_profile(
    p_org_id INTEGER,
    p_name VARCHAR(255) DEFAULT NULL,
    p_logo_url VARCHAR(1024) DEFAULT NULL,
    p_website VARCHAR(255) DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_industry VARCHAR(100) DEFAULT NULL,
    p_company_size VARCHAR(50) DEFAULT NULL
)
RETURNS TABLE (
    id INTEGER,
    name VARCHAR(255),
    logo_url VARCHAR(1024),
    website VARCHAR(255),
    description TEXT,
    industry VARCHAR(100),
    company_size VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE,
    owner_name VARCHAR(255),
    owner_email VARCHAR(255),
    members_count BIGINT,
    projects_count BIGINT
) AS $$
BEGIN
    UPDATE organizations
    SET
        name = COALESCE(p_name, organizations.name),
        logo_url = COALESCE(p_logo_url, organizations.logo_url),
        website = COALESCE(p_website, organizations.website),
        description = COALESCE(p_description, organizations.description),
        industry = COALESCE(p_industry, organizations.industry),
        company_size = COALESCE(p_company_size, organizations.company_size)
    WHERE organizations.id = p_org_id AND organizations.deleted_at IS NULL;

    RETURN QUERY
    SELECT * FROM fn_get_organization_profile(p_org_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
