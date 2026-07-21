-- 029_comment_functions.sql
-- Canonical view and stored functions for task comments

CREATE OR REPLACE VIEW v_comments_canonical AS
SELECT 
    c.id,
    c.task_id,
    c.user_id,
    c.parent_comment_id,
    c.content,
    c.created_at,
    c.deleted_at,
    u.first_name AS user_first_name,
    u.last_name AS user_last_name,
    u.avatar_url AS user_avatar_url,
    u.email AS user_email
FROM task_comments c
LEFT JOIN users u ON c.user_id = u.id
WHERE c.deleted_at IS NULL;

CREATE OR REPLACE FUNCTION fn_create_comment(
    p_task_id INTEGER,
    p_user_id INTEGER,
    p_parent_comment_id INTEGER,
    p_content TEXT,
    p_org_id INTEGER
) RETURNS INTEGER AS $$
DECLARE
    v_comment_id INTEGER;
    v_activity_id INTEGER;
BEGIN
    INSERT INTO task_comments (task_id, user_id, parent_comment_id, content)
    VALUES (p_task_id, p_user_id, p_parent_comment_id, p_content)
    RETURNING id INTO v_comment_id;

    INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, new_value)
    VALUES (p_org_id, 'COMMENT', p_task_id, p_user_id, 'COMMENT_ADDED', jsonb_build_object('content', 'New comment added'))
    RETURNING id INTO v_activity_id;

    RETURN v_comment_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_delete_comment(
    p_comment_id INTEGER,
    p_user_id INTEGER,
    p_user_role VARCHAR,
    p_org_id INTEGER
) RETURNS BOOLEAN AS $$
DECLARE
    v_comment_user_id INTEGER;
    v_task_id INTEGER;
    v_org_id INTEGER;
BEGIN
    SELECT c.user_id, c.task_id, b.organization_id 
    INTO v_comment_user_id, v_task_id, v_org_id
    FROM task_comments c
    JOIN tasks t ON c.task_id = t.id
    JOIN boards b ON t.board_id = b.id
    WHERE c.id = p_comment_id AND c.deleted_at IS NULL;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Comment not found';
    END IF;

    IF v_org_id != p_org_id THEN
        RAISE EXCEPTION 'Access denied';
    END IF;

    IF v_comment_user_id IS DISTINCT FROM p_user_id AND p_user_role NOT IN ('SUPER_ADMIN', 'MANAGER') THEN
        RAISE EXCEPTION 'Not authorized to delete this comment';
    END IF;

    UPDATE task_comments 
    SET deleted_at = CURRENT_TIMESTAMP 
    WHERE id = p_comment_id;

    INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, old_value, new_value)
    VALUES (p_org_id, 'COMMENT', v_task_id, p_user_id, 'COMMENT_DELETED', NULL, jsonb_build_object('comment_id', p_comment_id));

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
