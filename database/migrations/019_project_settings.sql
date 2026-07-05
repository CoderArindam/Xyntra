-- 019_project_settings.sql
-- Project settings and identity fields

ALTER TABLE boards 
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS icon VARCHAR(50),
    ADD COLUMN IF NOT EXISTS color VARCHAR(50),
    ADD COLUMN IF NOT EXISTS cover_gradient VARCHAR(50),
    ADD COLUMN IF NOT EXISTS default_assignee_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS project_lead_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP WITH TIME ZONE;

-- Recreate canonical view to include new fields
DROP VIEW IF EXISTS v_boards_canonical CASCADE;

CREATE OR REPLACE VIEW v_boards_canonical AS
SELECT
    b.id,
    b.organization_id,
    b.name,
    b.project_key,
    b.owner_id,
    b.description,
    b.icon,
    b.color,
    b.cover_gradient,
    b.default_assignee_id,
    b.project_lead_id,
    b.created_at,
    b.archived_at,
    (SELECT COUNT(*) FROM board_members WHERE board_id = b.id) AS member_count,
    (SELECT COUNT(*) FROM tasks WHERE board_id = b.id AND deleted_at IS NULL) AS task_count
FROM boards b
WHERE b.deleted_at IS NULL;

-- 1. Canonical Tasks View
CREATE OR REPLACE VIEW v_tasks_canonical AS
SELECT
    t.id,
    t.board_id,
    b.name AS board_name,
    b.organization_id,
    -- Construct human-friendly project key (e.g. ENG-24)
    (b.project_key || '-' || t.project_sequence_id) AS task_reference,
    t.column_id,
    c.name AS column_name,
    c.column_type,
    (c.column_type = 'DONE') AS is_completed, -- Derived completion state
    t.title,
    t.description,
    t.priority,
    t.due_date,
    t.reminder_at,
    t.completed_at,
    t.created_at,
    t.updated_at,
    
    -- Assignee Info
    t.assigned_to,
    au.email AS assignee_email,
    au.first_name AS assignee_first_name,
    au.last_name AS assignee_last_name,
    au.avatar_url AS assignee_avatar_url,
    
    -- Creator Info
    t.created_by,
    cu.email AS creator_email,
    cu.first_name AS creator_first_name,
    cu.last_name AS creator_last_name,
    cu.avatar_url AS creator_avatar_url

FROM tasks t
JOIN boards b ON t.board_id = b.id
JOIN board_columns c ON t.column_id = c.id
LEFT JOIN users au ON t.assigned_to = au.id
LEFT JOIN users cu ON t.created_by = cu.id
WHERE t.deleted_at IS NULL
  AND b.deleted_at IS NULL;

-- 3. Canonical Activities View
CREATE OR REPLACE VIEW v_activities_canonical AS
SELECT
    a.id,
    a.organization_id,
    a.entity_type,
    a.entity_id,
    a.activity_type,
    a.old_value,
    a.new_value,
    a.metadata,
    a.created_at,
    
    -- Actor Info
    a.user_id AS actor_id,
    u.first_name AS actor_first_name,
    u.last_name AS actor_last_name,
    u.avatar_url AS actor_avatar_url,
    u.email AS actor_email,
    
    -- Target Reference (e.g. ENG-24)
    CASE 
        WHEN a.entity_type = 'TASK' THEN (SELECT task_reference FROM v_tasks_canonical WHERE id = a.entity_id)
        WHEN a.entity_type = 'BOARD' THEN (SELECT project_key FROM v_boards_canonical WHERE id = a.entity_id)
        WHEN a.entity_type = 'COMMENT' THEN (SELECT task_reference FROM v_tasks_canonical WHERE id = a.entity_id)
        ELSE NULL
    END AS target_reference

FROM activities a
LEFT JOIN users u ON a.user_id = u.id;

-- 4. Canonical Notifications View
CREATE OR REPLACE VIEW v_notifications_canonical AS
SELECT
    n.id,
    n.user_id,
    n.is_read,
    n.created_at,
    
    -- Embedded Activity
    a.id AS activity_id,
    a.entity_type AS activity_entity_type,
    a.entity_id AS activity_entity_id,
    a.activity_type,
    a.target_reference AS activity_target_reference,
    a.actor_first_name AS activity_actor_first_name,
    a.actor_last_name AS activity_actor_last_name,
    a.actor_avatar_url AS activity_actor_avatar_url

FROM notifications n
JOIN v_activities_canonical a ON n.activity_id = a.id;


-- Function to get basic project settings
CREATE OR REPLACE FUNCTION fn_get_project_settings(p_board_id INTEGER)
RETURNS TABLE (
    id INTEGER,
    organization_id INTEGER,
    name VARCHAR(255),
    project_key VARCHAR(10),
    owner_id INTEGER,
    description TEXT,
    icon VARCHAR(50),
    color VARCHAR(50),
    cover_gradient VARCHAR(50),
    default_assignee_id INTEGER,
    project_lead_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE,
    member_count BIGINT,
    task_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.id,
        v.organization_id,
        v.name,
        v.project_key,
        v.owner_id,
        v.description,
        v.icon,
        v.color,
        v.cover_gradient,
        v.default_assignee_id,
        v.project_lead_id,
        v.created_at,
        v.archived_at,
        v.member_count,
        v.task_count
    FROM v_boards_canonical v
    WHERE v.id = p_board_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Function to get heavy aggregations (statistics)
CREATE OR REPLACE FUNCTION fn_get_project_statistics(p_board_id INTEGER)
RETURNS TABLE (
    total_tasks BIGINT,
    completed_tasks BIGINT,
    overdue_tasks BIGINT,
    members_count BIGINT,
    columns_count BIGINT,
    last_activity TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*) FROM tasks WHERE board_id = p_board_id AND deleted_at IS NULL) AS total_tasks,
        
        (SELECT COUNT(*) FROM tasks t 
         JOIN board_columns c ON t.column_id = c.id 
         WHERE t.board_id = p_board_id AND c.column_type = 'DONE' AND t.deleted_at IS NULL) AS completed_tasks,
         
        (SELECT COUNT(*) FROM tasks t
         JOIN board_columns c ON t.column_id = c.id
         WHERE t.board_id = p_board_id 
           AND c.column_type != 'DONE' 
           AND t.due_date < CURRENT_TIMESTAMP 
           AND t.deleted_at IS NULL) AS overdue_tasks,
           
        (SELECT COUNT(*) FROM board_members WHERE board_id = p_board_id) AS members_count,
        
        (SELECT COUNT(*) FROM board_columns WHERE board_id = p_board_id) AS columns_count,
        
        (SELECT MAX(created_at) FROM activities WHERE entity_type = 'BOARD' AND entity_id = p_board_id) AS last_activity;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Function to update settings
CREATE OR REPLACE FUNCTION fn_update_project_settings(
    p_board_id INTEGER,
    p_name VARCHAR(255) DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_icon VARCHAR(50) DEFAULT NULL,
    p_color VARCHAR(50) DEFAULT NULL,
    p_cover_gradient VARCHAR(50) DEFAULT NULL,
    p_default_assignee_id INTEGER DEFAULT -1, -- -1 means no update
    p_project_lead_id INTEGER DEFAULT -1 -- -1 means no update
)
RETURNS TABLE (
    id INTEGER,
    organization_id INTEGER,
    name VARCHAR(255),
    project_key VARCHAR(10),
    owner_id INTEGER,
    description TEXT,
    icon VARCHAR(50),
    color VARCHAR(50),
    cover_gradient VARCHAR(50),
    default_assignee_id INTEGER,
    project_lead_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE,
    member_count BIGINT,
    task_count BIGINT
) AS $$
BEGIN
    UPDATE boards
    SET
        name = COALESCE(p_name, boards.name),
        description = COALESCE(p_description, boards.description),
        icon = COALESCE(p_icon, boards.icon),
        color = COALESCE(p_color, boards.color),
        cover_gradient = COALESCE(p_cover_gradient, boards.cover_gradient),
        default_assignee_id = CASE WHEN p_default_assignee_id = -1 THEN boards.default_assignee_id ELSE p_default_assignee_id END,
        project_lead_id = CASE WHEN p_project_lead_id = -1 THEN boards.project_lead_id ELSE p_project_lead_id END
    WHERE boards.id = p_board_id AND boards.deleted_at IS NULL;

    RETURN QUERY
    SELECT * FROM fn_get_project_settings(p_board_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Function to archive project
CREATE OR REPLACE FUNCTION fn_archive_project(
    p_board_id INTEGER
)
RETURNS TABLE (
    id INTEGER,
    organization_id INTEGER,
    name VARCHAR(255),
    project_key VARCHAR(10),
    owner_id INTEGER,
    description TEXT,
    icon VARCHAR(50),
    color VARCHAR(50),
    cover_gradient VARCHAR(50),
    default_assignee_id INTEGER,
    project_lead_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE,
    member_count BIGINT,
    task_count BIGINT
) AS $$
BEGIN
    UPDATE boards
    SET archived_at = CURRENT_TIMESTAMP
    WHERE boards.id = p_board_id AND boards.deleted_at IS NULL AND boards.archived_at IS NULL;

    RETURN QUERY
    SELECT * FROM fn_get_project_settings(p_board_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
