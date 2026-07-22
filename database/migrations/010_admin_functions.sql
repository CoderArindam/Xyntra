-- 010_admin_functions.sql
-- User Defined Functions for Admin operations

CREATE OR REPLACE FUNCTION admin_get_all_users(p_org_id INTEGER)
RETURNS JSON AS $$
DECLARE
    v_result JSON;
BEGIN
    SELECT COALESCE(json_agg(row_to_json(u)), '[]'::json) INTO v_result
    FROM (
        SELECT id, email, role, created_at
        FROM users
        WHERE organization_id = p_org_id AND deleted_at IS NULL
        ORDER BY created_at DESC
    ) u;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION admin_create_user(
    p_email VARCHAR,
    p_password_hash VARCHAR,
    p_role role_enum,
    p_org_id INTEGER
)
RETURNS JSON AS $$
DECLARE
    v_user RECORD;
BEGIN
    INSERT INTO users (organization_id, email, password_hash, role, first_name)
    VALUES (p_org_id, p_email, p_password_hash, p_role, 'AdminUser')
    RETURNING id, email, role, created_at INTO v_user;
    
    RETURN row_to_json(v_user);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION admin_update_user_role(
    p_user_id INTEGER,
    p_role role_enum,
    p_org_id INTEGER
)
RETURNS JSON AS $$
DECLARE
    v_user RECORD;
BEGIN
    UPDATE users 
    SET role = p_role 
    WHERE id = p_user_id AND organization_id = p_org_id AND deleted_at IS NULL
    RETURNING id, email, role, created_at INTO v_user;
    
    IF v_user IS NULL THEN
        RETURN NULL;
    END IF;
    
    RETURN row_to_json(v_user);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION admin_delete_user(
    p_user_id INTEGER,
    p_org_id INTEGER
)
RETURNS BOOLEAN AS $$
DECLARE
    v_updated INTEGER;
BEGIN
    UPDATE users 
    SET deleted_at = CURRENT_TIMESTAMP 
    WHERE id = p_user_id AND organization_id = p_org_id AND deleted_at IS NULL;
    
    GET DIAGNOSTICS v_updated = ROW_COUNT;
    
    RETURN v_updated > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION admin_get_all_boards(p_org_id INTEGER)
RETURNS JSON AS $$
DECLARE
    v_result JSON;
BEGIN
    SELECT COALESCE(json_agg(row_to_json(b)), '[]'::json) INTO v_result
    FROM (
        SELECT id, name, owner_id, created_at, member_count
        FROM v_boards_canonical
        WHERE organization_id = p_org_id
        ORDER BY created_at DESC
    ) b;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION remove_user_from_board(
    p_board_id INTEGER,
    p_user_id INTEGER
)
RETURNS BOOLEAN AS $$
DECLARE
    v_target_role role_enum;
    v_deleted INTEGER;
BEGIN
    SELECT role INTO v_target_role FROM users WHERE id = p_user_id AND deleted_at IS NULL;

    IF v_target_role = 'SUPER_ADMIN' THEN
        RAISE EXCEPTION 'Cannot remove Super Admin from board';
    END IF;

    DELETE FROM board_members 
    WHERE board_id = p_board_id AND user_id = p_user_id;
    
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    
    RETURN v_deleted > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION get_board_members(p_board_id INTEGER)
RETURNS JSON AS $$
DECLARE
    v_result JSON;
BEGIN
    SELECT COALESCE(json_agg(row_to_json(m)), '[]'::json) INTO v_result
    FROM (
        SELECT 
            u.id, 
            u.email, 
            u.role, 
            bm.permission, 
            bm.created_at as joined_at
        FROM board_members bm
        JOIN users u ON bm.user_id = u.id
        WHERE bm.board_id = p_board_id AND u.deleted_at IS NULL
        ORDER BY bm.created_at ASC
    ) m;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
