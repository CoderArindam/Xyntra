-- 023_task_proposals_functions.sql
-- Stored procedures for task proposals management and review queue lifecycle

-- 0. Task creation stored function (reused during proposal approval)
CREATE OR REPLACE FUNCTION fn_create_task(
    p_board_id INTEGER,
    p_title VARCHAR,
    p_description TEXT DEFAULT NULL,
    p_assigned_to INTEGER DEFAULT NULL,
    p_created_by INTEGER DEFAULT NULL,
    p_column_id INTEGER DEFAULT NULL,
    p_priority VARCHAR DEFAULT 'MEDIUM',
    p_due_date TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    p_reminder_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
) RETURNS tasks AS $$
DECLARE
    v_column_id INTEGER := p_column_id;
    v_task tasks%ROWTYPE;
BEGIN
    IF v_column_id IS NULL THEN
        SELECT id INTO v_column_id
        FROM board_columns
        WHERE board_id = p_board_id
        ORDER BY position ASC
        LIMIT 1;
    END IF;

    IF v_column_id IS NULL THEN
        RAISE EXCEPTION 'No board column available for board %', p_board_id;
    END IF;

    INSERT INTO tasks (
        board_id, column_id, title, description, priority, assigned_to, created_by, due_date, reminder_at
    )
    VALUES (
        p_board_id, v_column_id, p_title, p_description, p_priority, p_assigned_to, p_created_by, p_due_date, p_reminder_at
    )
    RETURNING * INTO v_task;

    RETURN v_task;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 1. Authorization check for proposal review access
CREATE OR REPLACE FUNCTION fn_check_proposal_review_access(
    p_user_id INTEGER,
    p_org_id INTEGER
) RETURNS BOOLEAN AS $$
DECLARE
    v_has_access BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM users
        WHERE id = p_user_id
        AND organization_id = p_org_id
        AND UPPER(role::text) IN ('SUPER_ADMIN', 'MANAGER')
        AND deleted_at IS NULL
    ) INTO v_has_access;
    
    RETURN v_has_access;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 2. Create task proposal (status defaults to 'pending')
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
    RETURNING * INTO v_proposal;

    RETURN v_proposal;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 3. Update task proposal (pending state only)
CREATE OR REPLACE FUNCTION fn_update_task_proposal(
    p_proposal_id UUID,
    p_title TEXT DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_suggested_assignee_id INTEGER DEFAULT -1
) RETURNS task_proposals AS $$
DECLARE
    v_current_status task_proposal_status;
    v_proposal task_proposals%ROWTYPE;
BEGIN
    SELECT status INTO v_current_status
    FROM task_proposals
    WHERE id = p_proposal_id;

    IF v_current_status IS NULL THEN
        RAISE EXCEPTION 'Task proposal not found: %', p_proposal_id;
    END IF;

    IF v_current_status != 'pending' THEN
        RAISE EXCEPTION 'Cannot update proposal %: status is % (must be pending)', p_proposal_id, v_current_status;
    END IF;

    UPDATE task_proposals
    SET
        title = COALESCE(p_title, title),
        description = COALESCE(p_description, description),
        suggested_assignee_id = CASE WHEN p_suggested_assignee_id = -1 THEN suggested_assignee_id ELSE p_suggested_assignee_id END
    WHERE id = p_proposal_id
    RETURNING * INTO v_proposal;

    RETURN v_proposal;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 4. Approve task proposal (Single Atomic Transaction)
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

    -- Audit log entry
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


-- 5. Reject task proposal
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

    -- Audit log entry
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
