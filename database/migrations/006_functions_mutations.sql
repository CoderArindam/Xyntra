-- 006_functions_mutations.sql
-- Complex business logic mutations wrapped in transactions

CREATE OR REPLACE FUNCTION create_organization_with_admin(
    p_org_name VARCHAR,
    p_admin_email VARCHAR,
    p_admin_password_hash VARCHAR,
    p_admin_first_name VARCHAR,
    p_admin_last_name VARCHAR
) RETURNS INTEGER AS $$
DECLARE
    v_org_id INTEGER;
    v_user_id INTEGER;
BEGIN
    INSERT INTO organizations (name) VALUES (p_org_name) RETURNING id INTO v_org_id;

    INSERT INTO users (organization_id, email, password_hash, first_name, last_name, role)
    VALUES (v_org_id, p_admin_email, p_admin_password_hash, p_admin_first_name, p_admin_last_name, 'SUPER_ADMIN')
    RETURNING id INTO v_user_id;

    -- Basic audit log
    INSERT INTO audit_logs (organization_id, user_id, action, entity_type, entity_id, details)
    VALUES (v_org_id, v_user_id, 'ORGANIZATION_CREATED', 'ORGANIZATION', v_org_id, jsonb_build_object('name', p_org_name));

    RETURN v_org_id;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION accept_invitation(
    p_token VARCHAR,
    p_password_hash VARCHAR,
    p_first_name VARCHAR,
    p_last_name VARCHAR
) RETURNS INTEGER AS $$
DECLARE
    v_invitation RECORD;
    v_user_id INTEGER;
BEGIN
    SELECT * INTO v_invitation
    FROM organization_invitations
    WHERE token = p_token AND accepted_at IS NULL AND expires_at > CURRENT_TIMESTAMP;

    IF v_invitation IS NULL THEN
        RAISE EXCEPTION 'Invalid or expired invitation';
    END IF;

    -- Create user
    INSERT INTO users (organization_id, email, password_hash, first_name, last_name, role)
    VALUES (v_invitation.organization_id, v_invitation.email, p_password_hash, p_first_name, p_last_name, v_invitation.role)
    RETURNING id INTO v_user_id;

    -- Mark token accepted
    UPDATE organization_invitations
    SET accepted_at = CURRENT_TIMESTAMP
    WHERE id = v_invitation.id;

    -- Audit log
    INSERT INTO audit_logs (organization_id, user_id, action, entity_type, entity_id, details)
    VALUES (v_invitation.organization_id, v_user_id, 'INVITATION_ACCEPTED', 'USER', v_user_id, jsonb_build_object('email', v_invitation.email, 'role', v_invitation.role));

    RETURN v_user_id;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION assign_user_to_board(
    p_actor_id INTEGER,
    p_board_id INTEGER,
    p_target_user_id INTEGER,
    p_permission permission_enum
) RETURNS BOOLEAN AS $$
DECLARE
    v_org_id INTEGER;
    v_target_org_id INTEGER;
BEGIN
    -- Check permissions
    IF NOT can_manage_board(p_actor_id, p_board_id) THEN
        RAISE EXCEPTION 'Not authorized to manage board members';
    END IF;

    -- Check if target user is in the same org
    SELECT organization_id INTO v_org_id FROM boards WHERE id = p_board_id;
    SELECT organization_id INTO v_target_org_id FROM users WHERE id = p_target_user_id;

    IF v_org_id != v_target_org_id THEN
        RAISE EXCEPTION 'User does not belong to the board''s organization';
    END IF;

    INSERT INTO board_members (board_id, user_id, permission)
    VALUES (p_board_id, p_target_user_id, p_permission)
    ON CONFLICT (board_id, user_id) DO UPDATE SET permission = EXCLUDED.permission;

    -- Audit log
    INSERT INTO audit_logs (organization_id, user_id, action, entity_type, entity_id, details)
    VALUES (v_org_id, p_actor_id, 'BOARD_MEMBER_ASSIGNED', 'BOARD', p_board_id, jsonb_build_object('target_user_id', p_target_user_id, 'permission', p_permission));

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
