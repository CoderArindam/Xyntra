-- 026_meeting_sessions_org_scope.sql
-- Multi-org isolation and Google Calendar readiness for meeting_sessions

-- 1. Create meeting_source enum type
DO $$ BEGIN
    CREATE TYPE meeting_source AS ENUM ('manual', 'google_calendar');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Alter meeting_sessions table to add org_id, initiator, calendar fields, and source
ALTER TABLE meeting_sessions
ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS initiated_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS calendar_event_id TEXT NULL,
ADD COLUMN IF NOT EXISTS scheduled_start_time TIMESTAMP WITH TIME ZONE NULL,
ADD COLUMN IF NOT EXISTS source meeting_source NOT NULL DEFAULT 'manual';

-- 3. Backfill org_id for existing rows from task_proposals or default org 1, then enforce NOT NULL
UPDATE meeting_sessions ms
SET org_id = COALESCE(
    (SELECT tp.org_id FROM task_proposals tp WHERE tp.meeting_session_id = ms.id LIMIT 1),
    1
)
WHERE ms.org_id IS NULL;

ALTER TABLE meeting_sessions ALTER COLUMN org_id SET NOT NULL;

-- 4. Index on org_id for meeting_sessions
CREATE INDEX IF NOT EXISTS idx_meeting_sessions_org_id ON meeting_sessions(org_id);


-- 5. Shared internal helper for role check (SUPER_ADMIN or MANAGER)
CREATE OR REPLACE FUNCTION fn_check_user_has_management_role(
    p_user_id INTEGER,
    p_org_id INTEGER
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM users
        WHERE id = p_user_id
        AND organization_id = p_org_id
        AND UPPER(role::text) IN ('SUPER_ADMIN', 'MANAGER')
        AND deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 6. Public entry point for meeting initiation access check
CREATE OR REPLACE FUNCTION fn_check_meeting_initiation_access(
    p_user_id INTEGER,
    p_org_id INTEGER
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN fn_check_user_has_management_role(p_user_id, p_org_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 7. Update fn_check_proposal_review_access to use shared helper
CREATE OR REPLACE FUNCTION fn_check_proposal_review_access(
    p_user_id INTEGER,
    p_org_id INTEGER
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN fn_check_user_has_management_role(p_user_id, p_org_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 8. Stored procedure to create a meeting session explicitly scoped to an organization
CREATE OR REPLACE FUNCTION fn_create_meeting_session(
    p_org_id INTEGER,
    p_meeting_url TEXT,
    p_initiated_by_user_id INTEGER DEFAULT NULL,
    p_source meeting_source DEFAULT 'manual',
    p_calendar_event_id TEXT DEFAULT NULL,
    p_scheduled_start_time TIMESTAMP WITH TIME ZONE DEFAULT NULL
) RETURNS meeting_sessions AS $$
DECLARE
    v_session meeting_sessions%ROWTYPE;
BEGIN
    INSERT INTO meeting_sessions (
        org_id,
        meeting_url,
        initiated_by_user_id,
        source,
        calendar_event_id,
        scheduled_start_time,
        status
    ) VALUES (
        p_org_id,
        p_meeting_url,
        p_initiated_by_user_id,
        p_source,
        p_calendar_event_id,
        p_scheduled_start_time,
        'starting'
    )
    RETURNING * INTO v_session;

    RETURN v_session;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 9. Canonical view for meeting sessions
DROP VIEW IF EXISTS v_meeting_sessions_canonical CASCADE;
CREATE OR REPLACE VIEW v_meeting_sessions_canonical AS
SELECT
    ms.id,
    ms.session_id,
    ms.org_id,
    o.name AS org_name,
    ms.meeting_url,
    ms.status,
    ms.source,
    ms.calendar_event_id,
    ms.scheduled_start_time,
    ms.started_at,
    ms.created_at,
    
    -- Initiator Info
    ms.initiated_by_user_id,
    iu.email AS initiator_email,
    iu.first_name AS initiator_first_name,
    iu.last_name AS initiator_last_name,
    CASE 
        WHEN iu.first_name IS NOT NULL OR iu.last_name IS NOT NULL 
        THEN TRIM(CONCAT(iu.first_name, ' ', iu.last_name))
        ELSE iu.email 
    END AS initiator_display_name,
    iu.avatar_url AS initiator_avatar_url
FROM meeting_sessions ms
JOIN organizations o ON ms.org_id = o.id
LEFT JOIN users iu ON ms.initiated_by_user_id = iu.id;
