-- 011_invitation_functions.sql

CREATE OR REPLACE FUNCTION get_organization_invitations(p_org_id INTEGER)
RETURNS JSON AS $$
DECLARE
    v_result JSON;
BEGIN
    SELECT COALESCE(json_agg(row_to_json(i)), '[]'::json) INTO v_result
    FROM (
        SELECT 
            id, email, role, token, expires_at, created_at, accepted_at,
            (accepted_at IS NULL AND expires_at > CURRENT_TIMESTAMP) as is_pending
        FROM organization_invitations
        WHERE organization_id = p_org_id
        ORDER BY created_at DESC
    ) i;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION get_organization_by_id(p_org_id INTEGER)
RETURNS JSON AS $$
DECLARE
    v_result JSON;
BEGIN
    SELECT row_to_json(o) INTO v_result
    FROM (
        SELECT id, name, created_at
        FROM organizations
        WHERE id = p_org_id
    ) o;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


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
    INSERT INTO organization_invitations (organization_id, email, role, token, expires_at)
    VALUES (p_org_id, p_email, p_role, p_token, p_expires_at)
    RETURNING id, email, role, expires_at, created_at, accepted_at INTO v_invitation;
    
    RETURN row_to_json(v_invitation);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION get_invitation_by_token(p_token VARCHAR)
RETURNS JSON AS $$
DECLARE
    v_result JSON;
BEGIN
    SELECT row_to_json(i) INTO v_result
    FROM (
        SELECT 
            oi.id, 
            oi.organization_id, 
            o.name as org_name, 
            oi.email, 
            oi.role, 
            oi.expires_at, 
            oi.accepted_at
        FROM organization_invitations oi
        JOIN organizations o ON oi.organization_id = o.id
        WHERE oi.token = p_token
    ) i;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
