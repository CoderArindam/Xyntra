-- 044_timesheet_reports_views.sql
-- Timesheet Reports Canonical Views & Notification Stored Procedure

-- 1. Extend entity_type_enum for timesheet notifications
DO $$ BEGIN
    ALTER TYPE entity_type_enum ADD VALUE IF NOT EXISTS 'TIMESHEET';
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Stored Procedure for Timesheet Notification Creation
CREATE OR REPLACE FUNCTION fn_create_timesheet_notification(
    p_recipient_id UUID,
    p_actor_id UUID,
    p_title TEXT,
    p_body TEXT DEFAULT NULL,
    p_deep_link TEXT DEFAULT NULL,
    p_timesheet_id UUID DEFAULT NULL,
    p_activity_type TEXT DEFAULT 'CREATED'
)
RETURNS INTEGER AS $$
DECLARE
    v_org_id UUID;
    v_actor_int_id INTEGER;
    v_recipient_int_id INTEGER;
    v_activity_id INTEGER;
    v_notification_id INTEGER;
BEGIN
    SELECT organization_id INTO v_org_id FROM users WHERE id::text = p_actor_id::text;
    IF v_org_id IS NULL AND p_recipient_id IS NOT NULL THEN
        SELECT organization_id INTO v_org_id FROM users WHERE id::text = p_recipient_id::text;
    END IF;

    SELECT id INTO v_actor_int_id FROM users WHERE id::text = p_actor_id::text;
    SELECT id INTO v_recipient_int_id FROM users WHERE id::text = p_recipient_id::text;

    IF v_recipient_int_id IS NULL THEN
        RETURN NULL;
    END IF;

    INSERT INTO activities (
        organization_id,
        entity_type,
        entity_id,
        user_id,
        activity_type,
        new_value,
        metadata
    )
    VALUES (
        v_org_id::integer,
        'TIMESHEET'::entity_type_enum,
        0,
        v_actor_int_id,
        'CREATED'::activity_type_enum,
        jsonb_build_object(
            'title', p_title,
            'body', p_body,
            'deep_link', p_deep_link,
            'timesheet_id', p_timesheet_id
        ),
        jsonb_build_object('deep_link', p_deep_link)
    )
    RETURNING id INTO v_activity_id;

    INSERT INTO notifications (user_id, activity_id, is_read)
    VALUES (v_recipient_int_id, v_activity_id, false)
    RETURNING id INTO v_notification_id;

    RETURN v_notification_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 3. v_timesheet_org_summary_canonical
CREATE OR REPLACE VIEW v_timesheet_org_summary_canonical AS
SELECT
    t.org_id,
    t.week_start_date,
    COUNT(DISTINCT t.user_id) FILTER (WHERE t.status != 'draft')::INTEGER AS total_members_who_submitted,
    COUNT(*) FILTER (WHERE t.status != 'draft')::INTEGER AS total_timesheets_submitted,
    COUNT(*) FILTER (WHERE t.status = 'approved')::INTEGER AS total_timesheets_approved,
    COUNT(*) FILTER (WHERE t.status = 'rejected')::INTEGER AS total_timesheets_rejected,
    COUNT(*) FILTER (WHERE t.status = 'submitted')::INTEGER AS total_timesheets_pending,
    COALESCE(SUM(t.total_hours), 0.00)::NUMERIC(10,2) AS total_hours_logged,
    ROUND(
        COALESCE(SUM(t.total_hours), 0.00) / 
        NULLIF(COUNT(DISTINCT t.user_id) FILTER (WHERE t.status != 'draft'), 0),
        2
    )::NUMERIC(10,2) AS avg_hours_per_member,
    ROUND(
        (COUNT(DISTINCT t.user_id) FILTER (WHERE t.status != 'draft'))::NUMERIC / 
        NULLIF((
            SELECT COUNT(*) 
            FROM users u 
            WHERE u.organization_id::text = t.org_id::text AND u.deleted_at IS NULL
        ), 0)::NUMERIC * 100.0,
        2
    )::NUMERIC(5,2) AS compliance_rate
FROM timesheets t
GROUP BY t.org_id, t.week_start_date;


-- 4. v_timesheet_member_summary_canonical
CREATE OR REPLACE VIEW v_timesheet_member_summary_canonical AS
SELECT
    u.id AS user_id,
    u.organization_id AS org_id,
    COALESCE(NULLIF(TRIM(CONCAT(u.first_name, ' ', u.last_name)), ''), u.email) AS display_name,
    u.email,
    t.week_start_date,
    COALESCE(t.status, 'draft'::timesheet_status) AS status,
    COALESCE(t.total_hours, 0.00)::NUMERIC(10,2) AS total_hours,
    CASE
        WHEN t.submitted_at IS NOT NULL THEN (
            t.submitted_at::DATE <= (t.week_end_date + COALESCE(p.submission_deadline_days, 2))
        )
        ELSE false
    END AS is_on_time
FROM users u
JOIN timesheets t ON t.user_id::text = u.id::text AND t.org_id::text = u.organization_id::text
LEFT JOIN timesheet_policies p ON p.org_id::text = u.organization_id::text
WHERE u.deleted_at IS NULL;


-- 5. v_timesheet_board_hours_canonical
CREATE OR REPLACE VIEW v_timesheet_board_hours_canonical AS
SELECT
    b.id AS board_id,
    b.name AS board_name,
    b.organization_id AS org_id,
    t.week_start_date,
    COALESCE(SUM(e.hours), 0.00)::NUMERIC(10,2) AS total_hours_logged,
    COUNT(DISTINCT e.user_id)::INTEGER AS member_count
FROM timesheet_entries e
JOIN timesheets t ON t.id = e.timesheet_id
JOIN boards b ON b.id::text = e.board_id::text
GROUP BY b.id, b.name, b.organization_id, t.week_start_date;
