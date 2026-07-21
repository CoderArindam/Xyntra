-- 036_dashboard_views.sql
-- Canonical views for Manager/Superadmin Dashboard

-- 1. Canonical view for Organization-wide Dashboard KPIs
DROP VIEW IF EXISTS v_dashboard_kpis_canonical CASCADE;
CREATE OR REPLACE VIEW v_dashboard_kpis_canonical AS
SELECT 
    o.id AS organization_id,
    o.name AS organization_name,
    
    -- Task counts by status
    COALESCE(t_stats.total_tasks, 0) AS total_tasks,
    COALESCE(t_stats.todo_tasks, 0) AS todo_tasks,
    COALESCE(t_stats.in_progress_tasks, 0) AS in_progress_tasks,
    COALESCE(t_stats.review_tasks, 0) AS review_tasks,
    COALESCE(t_stats.done_tasks, 0) AS done_tasks,
    COALESCE(t_stats.overdue_tasks, 0) AS overdue_tasks,
    
    -- Org stats
    COALESCE(b_stats.total_boards, 0) AS total_boards,
    COALESCE(u_stats.total_team_members, 0) AS total_team_members,
    COALESCE(tp_stats.pending_proposals_count, 0) AS pending_proposals_count,
    COALESCE(ms_stats.active_meetings_count, 0) AS active_meetings_count

FROM organizations o

-- Aggregate Task Stats per Organization
LEFT JOIN (
    SELECT 
        b.organization_id,
        COUNT(t.id) AS total_tasks,
        COUNT(t.id) FILTER (WHERE c.column_type = 'TODO' AND LOWER(c.name) NOT LIKE '%review%') AS todo_tasks,
        COUNT(t.id) FILTER (WHERE c.column_type = 'IN_PROGRESS' AND LOWER(c.name) NOT LIKE '%review%') AS in_progress_tasks,
        COUNT(t.id) FILTER (WHERE LOWER(c.name) LIKE '%review%' OR c.column_type::text = 'REVIEW') AS review_tasks,
        COUNT(t.id) FILTER (WHERE c.column_type = 'DONE') AS done_tasks,
        COUNT(t.id) FILTER (WHERE t.due_date < CURRENT_TIMESTAMP AND c.column_type != 'DONE') AS overdue_tasks
    FROM tasks t
    JOIN boards b ON t.board_id = b.id
    JOIN board_columns c ON t.column_id = c.id
    WHERE t.deleted_at IS NULL
      AND b.deleted_at IS NULL
    GROUP BY b.organization_id
) t_stats ON o.id = t_stats.organization_id

-- Aggregate Board Stats per Organization
LEFT JOIN (
    SELECT 
        organization_id,
        COUNT(*) AS total_boards
    FROM boards
    WHERE deleted_at IS NULL
      AND archived_at IS NULL
    GROUP BY organization_id
) b_stats ON o.id = b_stats.organization_id

-- Aggregate Team Member Stats per Organization
LEFT JOIN (
    SELECT 
        organization_id,
        COUNT(*) AS total_team_members
    FROM users
    WHERE deleted_at IS NULL
    GROUP BY organization_id
) u_stats ON o.id = u_stats.organization_id

-- Aggregate Pending Task Proposals per Organization
LEFT JOIN (
    SELECT 
        org_id AS organization_id,
        COUNT(*) AS pending_proposals_count
    FROM task_proposals
    WHERE status::text = 'pending'
    GROUP BY org_id
) tp_stats ON o.id = tp_stats.organization_id

-- Aggregate Active Meeting Sessions per Organization
LEFT JOIN (
    SELECT 
        org_id AS organization_id,
        COUNT(*) AS active_meetings_count
    FROM meeting_sessions
    WHERE LOWER(status) NOT IN ('completed', 'failed', 'finished', 'terminated', 'disconnected', 'meeting_ended', 'meeting_not_found', 'permission_denied', 'network_failure', 'login_required', 'unknown_error')
    GROUP BY org_id
) ms_stats ON o.id = ms_stats.organization_id;


-- 2. Canonical view for Per-Board Dashboard Summaries
DROP VIEW IF EXISTS v_dashboard_board_summaries_canonical CASCADE;
CREATE OR REPLACE VIEW v_dashboard_board_summaries_canonical AS
SELECT
    b.id,
    b.id AS board_id,
    b.organization_id,
    b.name,
    b.name AS board_name,
    b.project_key,
    b.description,
    b.icon,
    b.color,
    b.cover_gradient,
    b.created_at,
    (SELECT COUNT(*) FROM board_members WHERE board_id = b.id) AS member_count,
    COALESCE(t_summary.task_count, 0) AS task_count,
    COALESCE(t_summary.completed_task_count, 0) AS completed_task_count,
    CASE 
        WHEN COALESCE(t_summary.task_count, 0) > 0 
        THEN ROUND((COALESCE(t_summary.completed_task_count, 0)::numeric / t_summary.task_count::numeric) * 100.0, 1)::float
        ELSE 0.0 
    END AS completion_percentage,
    COALESCE(t_summary.overdue_count, 0) AS overdue_count
FROM boards b
LEFT JOIN (
    SELECT 
        t.board_id,
        COUNT(t.id) AS task_count,
        COUNT(t.id) FILTER (WHERE c.column_type = 'DONE') AS completed_task_count,
        COUNT(t.id) FILTER (WHERE t.due_date < CURRENT_TIMESTAMP AND c.column_type != 'DONE') AS overdue_count
    FROM tasks t
    JOIN board_columns c ON t.column_id = c.id
    WHERE t.deleted_at IS NULL
    GROUP BY t.board_id
) t_summary ON b.id = t_summary.board_id
WHERE b.deleted_at IS NULL;
