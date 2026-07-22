-- 032_revoke_invitation_function.sql

CREATE OR REPLACE FUNCTION revoke_invitation(
    p_invitation_id INTEGER,
    p_org_id INTEGER
)
RETURNS JSON AS $$
DECLARE
    v_invitation RECORD;
BEGIN
    DELETE FROM organization_invitations
    WHERE id = p_invitation_id AND organization_id = p_org_id AND accepted_at IS NULL
    RETURNING id, email, role, expires_at, created_at, accepted_at INTO v_invitation;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pending invitation not found or already accepted';
    END IF;

    RETURN row_to_json(v_invitation);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
