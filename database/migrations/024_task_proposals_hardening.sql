-- 024_task_proposals_hardening.sql
-- Duplicate proposal guard and audit logging for task proposals

-- 1. Add unique constraint to prevent duplicate pending proposals per meeting and title
DO $$ BEGIN
    ALTER TABLE task_proposals
    ADD CONSTRAINT task_proposals_session_title_key UNIQUE (meeting_session_id, title);
EXCEPTION
    WHEN duplicate_table OR duplicate_object THEN null;
END $$;


-- 2. Update fn_create_task_proposal with duplicate guard (ON CONFLICT)
CREATE OR REPLACE FUNCTION fn_create_task_proposal(
    p_org_id INTEGER,
    p_board_id INTEGER,
    p_meeting_session_id UUID,
    p_title TEXT,
    p_description TEXT DEFAULT NULL,
    p_suggested_assignee_id INTEGER DEFAULT NULL,
    p_confidence_score NUMERIC(3,2) DEFAULT NULL,
    p_source_transcript_quote TEXT DEFAULT NULL,
    p_raw_llm_payload JSONB DEFAULT NULL
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
        raw_llm_payload
    ) VALUES (
        p_org_id,
        p_board_id,
        p_meeting_session_id,
        p_title,
        p_description,
        p_suggested_assignee_id,
        p_confidence_score,
        p_source_transcript_quote,
        'pending',
        p_raw_llm_payload
    )
    ON CONFLICT (meeting_session_id, title) DO UPDATE SET
        description = COALESCE(EXCLUDED.description, task_proposals.description),
        suggested_assignee_id = COALESCE(EXCLUDED.suggested_assignee_id, task_proposals.suggested_assignee_id),
        confidence_score = COALESCE(EXCLUDED.confidence_score, task_proposals.confidence_score),
        source_transcript_quote = COALESCE(EXCLUDED.source_transcript_quote, task_proposals.source_transcript_quote),
        raw_llm_payload = COALESCE(EXCLUDED.raw_llm_payload, task_proposals.raw_llm_payload)
    WHERE task_proposals.status = 'pending'
    RETURNING * INTO v_proposal;

    IF v_proposal.id IS NULL THEN
        SELECT * INTO v_proposal
        FROM task_proposals
        WHERE meeting_session_id = p_meeting_session_id AND title = p_title;
    END IF;

    RETURN v_proposal;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 3. Update fn_approve_task_proposal with activity audit trail
CREATE OR REPLACE FUNCTION fn_approve_task_proposal(
    p_proposal_id UUID,
    p_reviewer_id INTEGER
) RETURNS tasks AS $$
DECLARE
    v_proposal task_proposals%ROWTYPE;
    v_created_task tasks%ROWTYPE;
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

    -- Create task via stored procedure
    v_created_task := fn_create_task(
        p_board_id := v_proposal.board_id,
        p_title := v_proposal.title,
        p_description := v_proposal.description,
        p_assigned_to := v_proposal.suggested_assignee_id,
        p_created_by := p_reviewer_id
    );

    -- Update proposal status and link resulting task ID
    UPDATE task_proposals
    SET
        status = 'approved',
        reviewed_by = p_reviewer_id,
        reviewed_at = CURRENT_TIMESTAMP,
        created_task_id = v_created_task.id
    WHERE id = p_proposal_id;

    -- 1. Log to activities table (Audit Trail)
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
            'confidence_score', v_proposal.confidence_score
        )
    );

    -- 2. Log to audit_logs table
    INSERT INTO audit_logs (organization_id, user_id, action, entity_type, entity_id, details)
    VALUES (
        v_proposal.org_id,
        p_reviewer_id,
        'TASK_PROPOSAL_APPROVED',
        'TASK',
        v_created_task.id,
        jsonb_build_object(
            'proposal_id', p_proposal_id,
            'meeting_session_id', v_proposal.meeting_session_id,
            'task_id', v_created_task.id
        )
    );

    RETURN v_created_task;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 4. Update fn_reject_task_proposal with activity audit trail
CREATE OR REPLACE FUNCTION fn_reject_task_proposal(
    p_proposal_id UUID,
    p_reviewer_id INTEGER
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
        RAISE EXCEPTION 'Cannot reject proposal %: status is % (must be pending)', p_proposal_id, v_proposal.status;
    END IF;

    UPDATE task_proposals
    SET
        status = 'rejected',
        reviewed_by = p_reviewer_id,
        reviewed_at = CURRENT_TIMESTAMP
    WHERE id = p_proposal_id
    RETURNING * INTO v_proposal;

    -- 1. Log to activities table (Audit Trail)
    INSERT INTO activities (
        organization_id,
        entity_type,
        entity_id,
        user_id,
        activity_type,
        old_value,
        new_value,
        metadata
    ) VALUES (
        v_proposal.org_id,
        'ORGANIZATION'::entity_type_enum,
        v_proposal.org_id,
        p_reviewer_id,
        'UPDATED'::activity_type_enum,
        jsonb_build_object('status', 'pending'),
        jsonb_build_object('status', 'rejected'),
        jsonb_build_object(
            'proposal_id', p_proposal_id,
            'meeting_session_id', v_proposal.meeting_session_id,
            'title', v_proposal.title,
            'action', 'REJECT_TASK_PROPOSAL'
        )
    );

    -- 2. Log to audit_logs table
    INSERT INTO audit_logs (organization_id, user_id, action, entity_type, entity_id, details)
    VALUES (
        v_proposal.org_id,
        p_reviewer_id,
        'TASK_PROPOSAL_REJECTED',
        'ORGANIZATION',
        v_proposal.org_id,
        jsonb_build_object(
            'proposal_id', p_proposal_id,
            'meeting_session_id', v_proposal.meeting_session_id
        )
    );

    RETURN v_proposal;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
