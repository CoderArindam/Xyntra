-- 012_authz_refinements.sql

CREATE OR REPLACE FUNCTION can_view_board(p_user_id INTEGER, p_board_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_role role_enum;
    v_org_id INTEGER;
    v_board_org_id INTEGER;
    v_is_member BOOLEAN;
    v_is_owner BOOLEAN;
BEGIN
    SELECT role, organization_id INTO v_role, v_org_id 
    FROM users WHERE id = p_user_id AND deleted_at IS NULL;
    
    IF v_role IS NULL THEN RETURN FALSE; END IF;

    SELECT organization_id, owner_id = p_user_id INTO v_board_org_id, v_is_owner
    FROM boards WHERE id = p_board_id AND deleted_at IS NULL;

    IF v_board_org_id IS NULL OR v_board_org_id != v_org_id THEN RETURN FALSE; END IF;

    IF v_role IN ('MANAGER', 'SUPER_ADMIN') THEN RETURN TRUE; END IF;
    IF v_is_owner THEN RETURN TRUE; END IF;

    SELECT EXISTS (
        SELECT 1 FROM board_members 
        WHERE board_id = p_board_id AND user_id = p_user_id
    ) INTO v_is_member;

    RETURN v_is_member;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION can_edit_board(p_user_id INTEGER, p_board_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_role role_enum;
    v_org_id INTEGER;
    v_board_org_id INTEGER;
    v_has_permission BOOLEAN;
    v_is_owner BOOLEAN;
BEGIN
    SELECT role, organization_id INTO v_role, v_org_id 
    FROM users WHERE id = p_user_id AND deleted_at IS NULL;
    
    IF v_role IS NULL THEN RETURN FALSE; END IF;

    SELECT organization_id, owner_id = p_user_id INTO v_board_org_id, v_is_owner
    FROM boards WHERE id = p_board_id AND deleted_at IS NULL;

    IF v_board_org_id IS NULL OR v_board_org_id != v_org_id THEN RETURN FALSE; END IF;

    IF v_role IN ('MANAGER', 'SUPER_ADMIN') THEN RETURN TRUE; END IF;
    IF v_is_owner THEN RETURN TRUE; END IF;

    SELECT EXISTS (
        SELECT 1 FROM board_members 
        WHERE board_id = p_board_id AND user_id = p_user_id AND permission IN ('EDITOR', 'OWNER')
    ) INTO v_has_permission;

    RETURN v_has_permission;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION can_manage_board(p_user_id INTEGER, p_board_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_role role_enum;
    v_org_id INTEGER;
    v_board_org_id INTEGER;
    v_has_permission BOOLEAN;
    v_is_owner BOOLEAN;
BEGIN
    SELECT role, organization_id INTO v_role, v_org_id 
    FROM users WHERE id = p_user_id AND deleted_at IS NULL;
    
    IF v_role IS NULL THEN RETURN FALSE; END IF;

    SELECT organization_id, owner_id = p_user_id INTO v_board_org_id, v_is_owner
    FROM boards WHERE id = p_board_id AND deleted_at IS NULL;

    IF v_board_org_id IS NULL OR v_board_org_id != v_org_id THEN RETURN FALSE; END IF;

    IF v_role IN ('MANAGER', 'SUPER_ADMIN') THEN RETURN TRUE; END IF;
    IF v_is_owner THEN RETURN TRUE; END IF;

    SELECT EXISTS (
        SELECT 1 FROM board_members 
        WHERE board_id = p_board_id AND user_id = p_user_id AND permission = 'OWNER'
    ) INTO v_has_permission;

    RETURN v_has_permission;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
