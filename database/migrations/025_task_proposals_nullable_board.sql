-- 025_task_proposals_nullable_board.sql
-- Patch task_proposals table to allow nullable board_id and add board resolution metadata

-- 1. Make board_id nullable on task_proposals
ALTER TABLE task_proposals ALTER COLUMN board_id DROP NOT NULL;

-- 2. Add board_confidence column with CHECK constraint
ALTER TABLE task_proposals
ADD COLUMN IF NOT EXISTS board_confidence NUMERIC(3,2) NULL
CHECK (board_confidence IS NULL OR (board_confidence >= 0 AND board_confidence <= 1));

-- 3. Create enum for board_resolution_source
DO $$ BEGIN
    CREATE TYPE board_resolution_source AS ENUM ('llm_matched', 'meeting_default', 'manager_assigned');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 4. Add board_source column
ALTER TABLE task_proposals
ADD COLUMN IF NOT EXISTS board_source board_resolution_source NULL;


-- 5. Update fn_create_task_proposal with nullable board_id and resolution metadata parameters
CREATE OR REPLACE FUNCTION fn_create_task_proposal(
    p_org_id INTEGER,
    p_board_id INTEGER DEFAULT NULL,
    p_meeting_session_id UUID DEFAULT NULL,
    p_title TEXT DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_suggested_assignee_id INTEGER DEFAULT NULL,
    p_confidence_score NUMERIC(3,2) DEFAULT NULL,
    p_source_transcript_quote TEXT DEFAULT NULL,
    p_raw_llm_payload JSONB DEFAULT NULL,
    p_board_confidence NUMERIC(3,2) DEFAULT NULL,
    p_board_source board_resolution_source DEFAULT NULL
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
        board_source
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
        p_raw_llm_payload,
        p_board_confidence,
        p_board_source
    )
    ON CONFLICT (meeting_session_id, title) DO UPDATE SET
        board_id = COALESCE(EXCLUDED.board_id, task_proposals.board_id),
        description = COALESCE(EXCLUDED.description, task_proposals.description),
        suggested_assignee_id = COALESCE(EXCLUDED.suggested_assignee_id, task_proposals.suggested_assignee_id),
        confidence_score = COALESCE(EXCLUDED.confidence_score, task_proposals.confidence_score),
        source_transcript_quote = COALESCE(EXCLUDED.source_transcript_quote, task_proposals.source_transcript_quote),
        raw_llm_payload = COALESCE(EXCLUDED.raw_llm_payload, task_proposals.raw_llm_payload),
        board_confidence = COALESCE(EXCLUDED.board_confidence, task_proposals.board_confidence),
        board_source = COALESCE(EXCLUDED.board_source, task_proposals.board_source)
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


-- 6. Update fn_update_task_proposal with optional p_board_id
CREATE OR REPLACE FUNCTION fn_update_task_proposal(
    p_proposal_id UUID,
    p_title TEXT DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_suggested_assignee_id INTEGER DEFAULT -1,
    p_board_id INTEGER DEFAULT NULL
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
        suggested_assignee_id = CASE WHEN p_suggested_assignee_id = -1 THEN suggested_assignee_id ELSE p_suggested_assignee_id END,
        board_id = COALESCE(p_board_id, board_id),
        board_source = CASE WHEN p_board_id IS NOT NULL THEN 'manager_assigned'::board_resolution_source ELSE board_source END
    WHERE id = p_proposal_id
    RETURNING * INTO v_proposal;

    RETURN v_proposal;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 7. Update fn_approve_task_proposal with board_id_override check
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

    -- Create task via stored procedure using final_board_id
    v_created_task := fn_create_task(
        p_board_id := v_final_board_id,
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
            'confidence_score', v_proposal.confidence_score,
            'board_id', v_final_board_id
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
            'task_id', v_created_task.id,
            'board_id', v_final_board_id
        )
    );

    RETURN v_created_task;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 8. Update v_task_proposals_canonical view to expose board_confidence and board_source
DROP VIEW IF EXISTS v_task_proposals_canonical CASCADE;
CREATE OR REPLACE VIEW v_task_proposals_canonical AS
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
LEFT JOIN boards b ON tp.board_id = b.id
LEFT JOIN meeting_sessions ms ON tp.meeting_session_id = ms.id
LEFT JOIN users su ON tp.suggested_assignee_id = su.id
LEFT JOIN users ru ON tp.reviewed_by = ru.id;
