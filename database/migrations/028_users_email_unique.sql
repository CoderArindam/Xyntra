-- 028_users_email_unique.sql
-- Enforce global email uniqueness on active users (where deleted_at IS NULL)
-- Also add canonical view for users (v_users_canonical) and update invitation procedure

-- 1. Create global unique index on users.email
CREATE UNIQUE INDEX IF NOT EXISTS users_email_unique_idx ON users (email) WHERE deleted_at IS NULL;

-- 2. Create canonical users view
CREATE OR REPLACE VIEW v_users_canonical AS
SELECT 
    id, 
    organization_id, 
    email, 
    first_name, 
    last_name, 
    avatar_url, 
    role, 
    is_email_verified, 
    created_at, 
    deleted_at
FROM users
WHERE deleted_at IS NULL;

-- 3. Update create_invitation to block invitations for existing registered users
CREATE OR REPLACE FUNCTION create_invitation(
    p_org_id INTEGER,
    p_email VARCHAR,
    p_role role_enum,
    p_token VARCHAR,
    p_expires_at TIMESTAMP WITH TIME ZONE
)
RETURNS JSON AS $$
DECLARE
    v_invitation RECORD;
BEGIN
    IF EXISTS (SELECT 1 FROM users WHERE email = p_email AND deleted_at IS NULL) THEN
        RAISE EXCEPTION 'This person is already a registered user';
    END IF;

    INSERT INTO organization_invitations (organization_id, email, role, token, expires_at)
    VALUES (p_org_id, p_email, p_role, p_token, p_expires_at)
    RETURNING id, email, role, expires_at, created_at, accepted_at INTO v_invitation;
    
    RETURN row_to_json(v_invitation);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
