-- 013_fix_task_authz.sql

CREATE OR REPLACE FUNCTION can_edit_task(p_user_id INTEGER, p_task_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_board_id INTEGER;
    v_assigned_to INTEGER;
BEGIN
    SELECT board_id, assigned_to INTO v_board_id, v_assigned_to
    FROM tasks
    WHERE id = p_task_id AND deleted_at IS NULL;
    
    IF v_board_id IS NULL THEN
        RETURN FALSE;
    END IF;

    -- The assigned user can always edit their own task
    IF v_assigned_to = p_user_id THEN
        RETURN TRUE;
    END IF;

    -- Otherwise, fall back to checking if they have editor permissions on the board
    RETURN can_edit_board(p_user_id, v_board_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
