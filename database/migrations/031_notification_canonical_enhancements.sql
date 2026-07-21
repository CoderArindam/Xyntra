-- 031_notification_canonical_enhancements.sql
-- Enhance v_activities_canonical and v_notifications_canonical to include payload values (old_value, new_value) and target_board_id

DROP VIEW IF EXISTS v_notifications_canonical CASCADE;
DROP VIEW IF EXISTS v_activities_canonical CASCADE;

CREATE VIEW v_activities_canonical AS
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
        WHEN a.entity_type = 'TASK' THEN (SELECT (b.project_key || '-' || t.project_sequence_id) FROM tasks t JOIN boards b ON t.board_id = b.id WHERE t.id = a.entity_id)
        WHEN a.entity_type = 'BOARD' THEN (SELECT project_key FROM boards WHERE id = a.entity_id)
        WHEN a.entity_type = 'COMMENT' THEN (SELECT (b.project_key || '-' || t.project_sequence_id) FROM tasks t JOIN boards b ON t.board_id = b.id WHERE t.id = a.entity_id)
        ELSE NULL
    END AS target_reference,

    -- Target Board ID for navigation
    CASE 
        WHEN a.entity_type = 'TASK' THEN (SELECT board_id FROM tasks WHERE id = a.entity_id)
        WHEN a.entity_type = 'BOARD' THEN a.entity_id
        WHEN a.entity_type = 'COMMENT' THEN (SELECT board_id FROM tasks WHERE id = a.entity_id)
        ELSE NULL
    END AS target_board_id

FROM activities a
LEFT JOIN users u ON a.user_id = u.id;


CREATE VIEW v_notifications_canonical AS
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
    a.old_value AS activity_old_value,
    a.new_value AS activity_new_value,
    a.target_reference AS activity_target_reference,
    a.target_board_id AS activity_target_board_id,
    a.actor_first_name AS activity_actor_first_name,
    a.actor_last_name AS activity_actor_last_name,
    a.actor_avatar_url AS activity_actor_avatar_url

FROM notifications n
JOIN v_activities_canonical a ON n.activity_id = a.id;
