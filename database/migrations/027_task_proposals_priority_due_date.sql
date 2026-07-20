-- 027_task_proposals_priority_due_date.sql
-- Add priority and due_date to task_proposals staging table and update views and stored functions

-- 1. Add columns to task_proposals table
ALTER TABLE task_proposals ADD COLUMN IF NOT EXISTS priority VARCHAR(50) DEFAULT 'MEDIUM';
ALTER TABLE task_proposals ADD COLUMN IF NOT EXISTS due_date TIMESTAMP WITH TIME ZONE;

-- 2. Drop dependent canonical view
DROP VIEW IF EXISTS v_task_proposals_canonical CASCADE;

-- 3. Recreate v_task_proposals_canonical with priority and due_date
CREATE VIEW v_task_proposals_canonical AS
SELECT
    tp.id,
    tp.org_id,
    o.name AS org_name,
    tp.board_id,
    b.name AS board_name,
    tp.board_confidence,
    tp.board_source,
    tp.meeting_session_id,
    ms.meeting_url,
    ms.started_at AS meeting_started_at,
    tp.title,
    tp.description,
    tp.priority,
    tp.due_date,
    tp.confidence_score,
    tp.source_transcript_quote,
    tp.status,
    tp.raw_llm_payload,
    tp.created_at,

    -- Suggested Assignee Metadata
    tp.suggested_assignee_id,
    sa.email AS suggested_assignee_email,
    sa.first_name AS suggested_assignee_first_name,
    sa.last_name AS suggested_assignee_last_name,
    TRIM(CONCAT(sa.first_name, ' ', sa.last_name)) AS suggested_assignee_display_name,
    sa.avatar_url AS suggested_assignee_avatar_url,

    -- Reviewer Metadata
    tp.reviewed_by,
    rev.email AS reviewer_email,
    rev.first_name AS reviewer_first_name,
    rev.last_name AS reviewer_last_name,
    TRIM(CONCAT(rev.first_name, ' ', rev.last_name)) AS reviewer_display_name,
    rev.avatar_url AS reviewer_avatar_url,
    tp.reviewed_at,

    -- Resulting Kanban Task Link
    tp.created_task_id
FROM task_proposals tp
JOIN organizations o ON tp.org_id = o.id
LEFT JOIN boards b ON tp.board_id = b.id
JOIN meeting_sessions ms ON tp.meeting_session_id = ms.id
LEFT JOIN users sa ON tp.suggested_assignee_id = sa.id
LEFT JOIN users rev ON tp.reviewed_by = rev.id;


-- 4. Recreate fn_create_task_proposal with priority and due_date
CREATE OR REPLACE FUNCTION fn_create_task_proposal(
    p_org_id INTEGER,
    p_board_id INTEGER,
    p_meeting_session_id UUID,
    p_title TEXT,
    p_description TEXT DEFAULT NULL,
    p_suggested_assignee_id INTEGER DEFAULT NULL,
    p_confidence_score NUMERIC(3,2) DEFAULT NULL,
    p_source_transcript_quote TEXT DEFAULT NULL,
    p_raw_llm_payload JSONB DEFAULT NULL,
    p_board_confidence NUMERIC(3,2) DEFAULT NULL,
    p_board_source board_resolution_source DEFAULT 'meeting_default',
    p_priority VARCHAR DEFAULT 'Medium',
    p_due_date TIMESTAMP WITH TIME ZONE DEFAULT NULL
) RETURNS task_proposals AS $$
DECLARE
    v_proposal task_proposals%ROWTYPE;
BEGIN
    INSERT INTO task_proposals (
        org_id,
        board_id,
        meeting_session_id,
        title,
        description,
        suggested_assignee_id,
        confidence_score,
        source_transcript_quote,
        status,
        raw_llm_payload,
        board_confidence,
        board_source,
        priority,
        due_date
    ) VALUES (
        p_org_id,
        p_board_id,
        p_meeting_session_id,
        p_title,
        p_description,
        p_suggested_assignee_id,
        p_confidence_score,
        p_source_transcript_quote,
        'pending'::task_proposal_status,
        p_raw_llm_payload,
        p_board_confidence,
        p_board_source,
        INITCAP(LOWER(COALESCE(p_priority, 'Medium'))),
        p_due_date
    )
    RETURNING * INTO v_proposal;

    RETURN v_proposal;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 5. Recreate fn_approve_task_proposal so fn_create_task receives priority and due_date
CREATE OR REPLACE FUNCTION fn_approve_task_proposal(
    p_proposal_id UUID,
    p_reviewer_id INTEGER,
    p_board_id_override INTEGER DEFAULT NULL
) RETURNS tasks AS $$
DECLARE
    v_proposal task_proposals%ROWTYPE;
    v_created_task tasks%ROWTYPE;
    v_final_board_id INTEGER;
BEGIN
    SELECT * INTO v_proposal
    FROM task_proposals
    WHERE id = p_proposal_id
    FOR UPDATE;

    IF v_proposal.id IS NULL THEN
        RAISE EXCEPTION 'Task proposal not found: %', p_proposal_id;
    END IF;

    IF v_proposal.status != 'pending' THEN
        RAISE EXCEPTION 'Cannot approve proposal %: status is % (must be pending)', p_proposal_id, v_proposal.status;
    END IF;

    -- Determine final board ID
    v_final_board_id := COALESCE(p_board_id_override, v_proposal.board_id);

    IF v_final_board_id IS NULL THEN
        RAISE EXCEPTION 'Cannot approve a task proposal without an assigned board';
    END IF;

    -- If board_id_override is provided and differs from proposal's current board_id, persist it
    IF p_board_id_override IS NOT NULL AND (v_proposal.board_id IS NULL OR v_proposal.board_id != p_board_id_override) THEN
        UPDATE task_proposals
        SET
            board_id = p_board_id_override,
            board_source = 'manager_assigned'::board_resolution_source
        WHERE id = p_proposal_id;
        
        v_proposal.board_id := p_board_id_override;
        v_proposal.board_source := 'manager_assigned'::board_resolution_source;
    END IF;

    -- Create task via stored procedure using final_board_id, priority, and due_date
    v_created_task := fn_create_task(
        p_board_id := v_final_board_id,
        p_title := v_proposal.title,
        p_description := v_proposal.description,
        p_assigned_to := v_proposal.suggested_assignee_id,
        p_created_by := p_reviewer_id,
        p_priority := INITCAP(LOWER(COALESCE(v_proposal.priority, 'Medium'))),
        p_due_date := v_proposal.due_date
    );

    -- Update proposal status and link resulting task ID
    UPDATE task_proposals
    SET
        status = 'approved',
        reviewed_by = p_reviewer_id,
        reviewed_at = CURRENT_TIMESTAMP,
        created_task_id = v_created_task.id
    WHERE id = p_proposal_id;

    -- Log audit activities
    INSERT INTO activities (
        organization_id,
        entity_type,
        entity_id,
        user_id,
        activity_type,
        new_value,
        metadata
    ) VALUES (
        v_proposal.org_id,
        'TASK'::entity_type_enum,
        v_created_task.id,
        p_reviewer_id,
        'CREATED'::activity_type_enum,
        jsonb_build_object(
            'title', v_created_task.title,
            'source', 'AI_MEETING_PROPOSAL',
            'proposal_id', p_proposal_id,
            'meeting_session_id', v_proposal.meeting_session_id
        ),
        jsonb_build_object(
            'proposal_id', p_proposal_id,
            'meeting_session_id', v_proposal.meeting_session_id,
            'confidence_score', v_proposal.confidence_score,
            'board_id', v_final_board_id
        )
    );

    RETURN v_created_task;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 6. Recreate fn_update_task_proposal to support updating priority and due_date
CREATE OR REPLACE FUNCTION fn_update_task_proposal(
    p_proposal_id UUID,
    p_title TEXT DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_suggested_assignee_id INTEGER DEFAULT -1,
    p_board_id INTEGER DEFAULT NULL,
    p_priority VARCHAR DEFAULT NULL,
    p_due_date TIMESTAMP WITH TIME ZONE DEFAULT NULL
) RETURNS task_proposals AS $$
DECLARE
    v_proposal task_proposals%ROWTYPE;
BEGIN
    SELECT * INTO v_proposal
    FROM task_proposals
    WHERE id = p_proposal_id
    FOR UPDATE;

    IF v_proposal.id IS NULL THEN
        RAISE EXCEPTION 'Task proposal not found: %', p_proposal_id;
    END IF;

    IF v_proposal.status != 'pending' THEN
        RAISE EXCEPTION 'Cannot edit proposal %: status is % (must be pending)', p_proposal_id, v_proposal.status;
    END IF;

    UPDATE task_proposals
    SET
        title = COALESCE(p_title, title),
        description = COALESCE(p_description, description),
        suggested_assignee_id = CASE
            WHEN p_suggested_assignee_id = -1 THEN suggested_assignee_id
            ELSE p_suggested_assignee_id
        END,
        board_id = COALESCE(p_board_id, board_id),
        board_source = CASE
            WHEN p_board_id IS NOT NULL AND (board_id IS NULL OR board_id != p_board_id) THEN 'manager_assigned'::board_resolution_source
            ELSE board_source
        END,
        priority = CASE WHEN p_priority IS NOT NULL THEN INITCAP(LOWER(p_priority)) ELSE priority END,
        due_date = COALESCE(p_due_date, due_date)
    WHERE id = p_proposal_id
    RETURNING * INTO v_proposal;

    RETURN v_proposal;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
