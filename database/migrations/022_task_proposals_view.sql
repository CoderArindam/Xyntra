-- 022_task_proposals_view.sql
-- Canonical view for task proposals to expose full details without N+1 queries

CREATE OR REPLACE VIEW v_task_proposals_canonical AS
SELECT
    tp.id,
    tp.org_id,
    o.name AS org_name,
    tp.board_id,
    b.name AS board_name,
    tp.meeting_session_id,
    ms.meeting_url,
    ms.started_at AS meeting_started_at,
    tp.title,
    tp.description,
    tp.confidence_score,
    tp.source_transcript_quote,
    tp.status,
    tp.raw_llm_payload,
    tp.created_at,
    
    -- Suggested Assignee Info
    tp.suggested_assignee_id,
    su.email AS suggested_assignee_email,
    su.first_name AS suggested_assignee_first_name,
    su.last_name AS suggested_assignee_last_name,
    CASE 
        WHEN su.first_name IS NOT NULL OR su.last_name IS NOT NULL 
        THEN TRIM(CONCAT(su.first_name, ' ', su.last_name))
        ELSE su.email 
    END AS suggested_assignee_display_name,
    su.avatar_url AS suggested_assignee_avatar_url,

    -- Reviewer Info
    tp.reviewed_by,
    ru.email AS reviewer_email,
    ru.first_name AS reviewer_first_name,
    ru.last_name AS reviewer_last_name,
    CASE 
        WHEN ru.first_name IS NOT NULL OR ru.last_name IS NOT NULL 
        THEN TRIM(CONCAT(ru.first_name, ' ', ru.last_name))
        ELSE ru.email 
    END AS reviewer_display_name,
    ru.avatar_url AS reviewer_avatar_url,
    tp.reviewed_at,

    -- Resulting Task Link
    tp.created_task_id
FROM task_proposals tp
JOIN organizations o ON tp.org_id = o.id
JOIN boards b ON tp.board_id = b.id
LEFT JOIN meeting_sessions ms ON tp.meeting_session_id = ms.id
LEFT JOIN users su ON tp.suggested_assignee_id = su.id
LEFT JOIN users ru ON tp.reviewed_by = ru.id;
