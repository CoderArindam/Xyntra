-- 008_views.sql
-- Canonical API Representations (Single Source of Truth)

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


-- 2. Canonical Boards View
CREATE OR REPLACE VIEW v_boards_canonical AS
SELECT
    b.id,
    b.organization_id,
    b.name,
    b.project_key,
    b.owner_id,
    b.created_at,
    (SELECT COUNT(*) FROM board_members WHERE board_id = b.id) AS member_count,
    (SELECT COUNT(*) FROM tasks WHERE board_id = b.id AND deleted_at IS NULL) AS task_count
FROM boards b
WHERE b.deleted_at IS NULL;


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

-- 5. Canonical Board Members View
CREATE OR REPLACE VIEW v_board_members_canonical AS
SELECT 
    bm.board_id,
    u.id, 
    u.email, 
    u.first_name, 
    u.last_name, 
    u.avatar_url, 
    bm.created_at as joined_at
FROM board_members bm
JOIN users u ON bm.user_id = u.id
WHERE u.deleted_at IS NULL

UNION

SELECT 
    b.id as board_id,
    u.id, 
    u.email, 
    u.first_name, 
    u.last_name, 
    u.avatar_url, 
    b.created_at as joined_at
FROM boards b
JOIN users u ON b.owner_id = u.id
WHERE u.deleted_at IS NULL;
