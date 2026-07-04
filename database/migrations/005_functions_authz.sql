-- 005_functions_authz.sql
-- Reusable PL/pgSQL authorization functions

CREATE OR REPLACE FUNCTION is_org_member(p_user_id INTEGER, p_org_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_is_member BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM users
        WHERE id = p_user_id
        AND organization_id = p_org_id
        AND deleted_at IS NULL
    ) INTO v_is_member;
    RETURN v_is_member;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION is_org_admin(p_user_id INTEGER, p_org_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_is_admin BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM users
        WHERE id = p_user_id
        AND organization_id = p_org_id
        AND role = 'SUPER_ADMIN'
        AND deleted_at IS NULL
    ) INTO v_is_admin;
    RETURN v_is_admin;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION is_org_manager_or_admin(p_user_id INTEGER, p_org_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_is_allowed BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM users
        WHERE id = p_user_id
        AND organization_id = p_org_id
        AND role IN ('MANAGER', 'SUPER_ADMIN')
        AND deleted_at IS NULL
    ) INTO v_is_allowed;
    RETURN v_is_allowed;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION can_view_board(p_user_id INTEGER, p_board_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_can_view BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM board_members bm
        JOIN users u ON bm.user_id = u.id
        WHERE bm.board_id = p_board_id
        AND bm.user_id = p_user_id
        AND u.deleted_at IS NULL
    ) INTO v_can_view;
    RETURN v_can_view;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION can_edit_board(p_user_id INTEGER, p_board_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_can_edit BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM board_members bm
        JOIN users u ON bm.user_id = u.id
        WHERE bm.board_id = p_board_id
        AND bm.user_id = p_user_id
        AND bm.permission IN ('EDITOR', 'OWNER')
        AND u.deleted_at IS NULL
    ) INTO v_can_edit;
    RETURN v_can_edit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION can_manage_board(p_user_id INTEGER, p_board_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_can_manage BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM board_members bm
        JOIN users u ON bm.user_id = u.id
        WHERE bm.board_id = p_board_id
        AND bm.user_id = p_user_id
        AND bm.permission = 'OWNER'
        AND u.deleted_at IS NULL
    ) INTO v_can_manage;
    RETURN v_can_manage;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION can_view_task(p_user_id INTEGER, p_task_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_board_id INTEGER;
BEGIN
    SELECT board_id INTO v_board_id
    FROM tasks
    WHERE id = p_task_id AND deleted_at IS NULL;
    
    IF v_board_id IS NULL THEN
        RETURN FALSE;
    END IF;

    RETURN can_view_board(p_user_id, v_board_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION can_edit_task(p_user_id INTEGER, p_task_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_board_id INTEGER;
BEGIN
    SELECT board_id INTO v_board_id
    FROM tasks
    WHERE id = p_task_id AND deleted_at IS NULL;
    
    IF v_board_id IS NULL THEN
        RETURN FALSE;
    END IF;

    RETURN can_edit_board(p_user_id, v_board_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
