-- 047_fix_rejected_timesheet_status.sql
-- Fix fn_reject_timesheet to set status = 'rejected' so rejected timesheets appear in Approval Queue -> Rejected section

CREATE OR REPLACE FUNCTION fn_reject_timesheet(
    p_timesheet_id UUID,
    p_approver_id UUID,
    p_comment TEXT DEFAULT NULL,
    p_ip_address INET DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL
)
RETURNS SETOF timesheets AS $$
DECLARE
    v_has_access BOOLEAN;
    v_status timesheet_status;
BEGIN
    v_has_access := fn_check_timesheet_approver_access(p_approver_id, p_timesheet_id);
    IF NOT v_has_access THEN
        RAISE EXCEPTION 'UNAUTHORIZED_APPROVER: Approver does not have access permission for this timesheet';
    END IF;

    SELECT status INTO v_status FROM timesheets WHERE id = p_timesheet_id FOR UPDATE;
    IF v_status != 'submitted' THEN
        RAISE EXCEPTION 'INVALID_STATUS: Only submitted timesheets can be rejected';
    END IF;

    -- Set status to 'rejected' (allows editing by member and visibility in Approver Rejected queue)
    UPDATE timesheets SET
        status = 'rejected',
        reviewed_at = NOW(),
        approver_id = p_approver_id,
        approver_comment = p_comment,
        updated_at = NOW()
    WHERE id = p_timesheet_id;

    INSERT INTO timesheet_audit_log (timesheet_id, actor_user_id, from_status, to_status, comment, ip_address, user_agent, created_at)
    VALUES (p_timesheet_id, p_approver_id, 'submitted', 'rejected', p_comment, p_ip_address, p_user_agent, NOW());

    RETURN QUERY SELECT * FROM timesheets WHERE id = p_timesheet_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Update fn_submit_timesheet to allow submitting both 'draft' AND 'rejected' timesheets
CREATE OR REPLACE FUNCTION fn_submit_timesheet(
    p_timesheet_id UUID,
    p_user_id UUID,
    p_member_note TEXT DEFAULT NULL,
    p_ip_address INET DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL,
    p_target_approver_id UUID DEFAULT NULL
)
RETURNS SETOF timesheets AS $$
DECLARE
    v_ts RECORD;
    v_policy RECORD;
    v_resolved_approver_id UUID := NULL;
BEGIN
    SELECT * INTO v_ts FROM timesheets WHERE id = p_timesheet_id FOR UPDATE;
    IF v_ts IS NULL THEN
        RAISE EXCEPTION 'TIMESHEET_NOT_FOUND: Timesheet does not exist';
    END IF;

    IF v_ts.user_id != p_user_id THEN
        RAISE EXCEPTION 'UNAUTHORIZED: User does not own this timesheet';
    END IF;

    IF (SELECT COUNT(*) FROM timesheet_entries WHERE timesheet_id = p_timesheet_id) = 0 THEN
        RAISE EXCEPTION 'EMPTY_TIMESHEET: Cannot submit an empty timesheet';
    END IF;

    IF v_ts.status = 'submitted' THEN
        RAISE EXCEPTION 'ALREADY_SUBMITTED: This timesheet has already been submitted';
    ELSIF v_ts.status NOT IN ('draft', 'rejected') THEN
        RAISE EXCEPTION 'INVALID_STATUS: Only draft or rejected timesheets can be submitted';
    END IF;

    SELECT * INTO v_policy FROM timesheet_policies WHERE (org_id::text = v_ts.org_id::text OR LTRIM(RIGHT(org_id::text, 12), '0') = LTRIM(RIGHT(v_ts.org_id::text, 12), '0'));
    IF CURRENT_DATE > (v_ts.week_end_date + COALESCE(v_policy.submission_deadline_days, 2)) THEN
        RAISE EXCEPTION 'SUBMISSION_DEADLINE_PASSED: Submission deadline passed on %', (v_ts.week_end_date + COALESCE(v_policy.submission_deadline_days, 2));
    END IF;

    -- Target approver resolution
    IF p_target_approver_id IS NOT NULL THEN
        v_resolved_approver_id := p_target_approver_id;
    ELSE
        SELECT approver_user_id INTO v_resolved_approver_id
        FROM timesheet_approver_assignments
        WHERE org_id = v_ts.org_id
          AND is_active = true
        ORDER BY created_at ASC
        LIMIT 1;
    END IF;

    UPDATE timesheets SET
        status = 'submitted',
        approver_id = v_resolved_approver_id,
        submitted_at = NOW(),
        member_note = p_member_note,
        updated_at = NOW()
    WHERE id = p_timesheet_id;

    INSERT INTO timesheet_audit_log (timesheet_id, actor_user_id, from_status, to_status, comment, ip_address, user_agent, created_at)
    VALUES (p_timesheet_id, p_user_id, v_ts.status, 'submitted', p_member_note, p_ip_address, p_user_agent, NOW());

    RETURN QUERY SELECT * FROM timesheets WHERE id = p_timesheet_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Update fn_upsert_timesheet_entry to allow modifying entries on 'draft' OR 'rejected' status
CREATE OR REPLACE FUNCTION fn_upsert_timesheet_entry(
    p_timesheet_id UUID,
    p_user_id UUID,
    p_board_id UUID,
    p_task_id UUID,
    p_entry_date DATE,
    p_hours NUMERIC(4,2),
    p_entry_type timesheet_entry_type DEFAULT 'task',
    p_description TEXT DEFAULT NULL,
    p_entry_id UUID DEFAULT NULL
)
RETURNS SETOF timesheet_entries AS $$
DECLARE
    v_status timesheet_status;
    v_ts_user_id UUID;
    v_org_id UUID;
    v_week_start DATE;
    v_week_end DATE;
    v_policy RECORD;
    v_existing_day_hours NUMERIC(4,2) := 0.00;
    v_new_day_hours NUMERIC(4,2);
    v_is_overtime BOOLEAN := false;
    v_result_entry timesheet_entries;
    v_task_assigned_to_int INTEGER;
BEGIN
    SELECT status, user_id, org_id, week_start_date, week_end_date
    INTO v_status, v_ts_user_id, v_org_id, v_week_start, v_week_end
    FROM timesheets WHERE id = p_timesheet_id FOR UPDATE;

    IF v_status IS NULL THEN
        RAISE EXCEPTION 'TIMESHEET_NOT_FOUND: Timesheet does not exist';
    END IF;

    IF v_ts_user_id != p_user_id THEN
        RAISE EXCEPTION 'UNAUTHORIZED: User does not own this timesheet';
    END IF;

    IF v_status IN ('submitted', 'approved') THEN
        RAISE EXCEPTION 'TIMESHEET_LOCKED: Entries can only be modified when status is draft or rejected';
    END IF;

    IF p_entry_date < v_week_start OR p_entry_date > v_week_end THEN
        RAISE EXCEPTION 'DATE_OUT_OF_WEEK_RANGE: Entry date must fall within week boundaries (% to %)', v_week_start, v_week_end;
    END IF;

    -- Strict Task Assignment Check
    IF p_task_id IS NOT NULL AND p_entry_type = 'task' THEN
        SELECT assigned_to INTO v_task_assigned_to_int
        FROM tasks
        WHERE (id::text = p_task_id::text OR id::text = LTRIM(RIGHT(p_task_id::text, 12), '0'));

        IF v_task_assigned_to_int IS NULL THEN
            RAISE EXCEPTION 'TASK_NOT_FOUND: Specified task does not exist';
        END IF;

        IF v_task_assigned_to_int::text != LTRIM(RIGHT(p_user_id::text, 12), '0') THEN
            RAISE EXCEPTION 'TASK_NOT_ASSIGNED: Time can only be logged against tasks assigned to you';
        END IF;
    END IF;

    -- Evaluate org policy limits
    SELECT * INTO v_policy FROM timesheet_policies WHERE (org_id::text = v_org_id::text OR LTRIM(RIGHT(org_id::text, 12), '0') = LTRIM(RIGHT(v_org_id::text, 12), '0'));

    IF v_policy IS NOT NULL THEN
        IF NOT COALESCE(v_policy.allow_future_entry, false) AND p_entry_date > CURRENT_DATE THEN
            RAISE EXCEPTION 'FUTURE_ENTRY_NOT_ALLOWED: Future date entries are restricted by organization policy';
        END IF;

        IF v_policy.allow_past_entry_days IS NOT NULL AND p_entry_date < (CURRENT_DATE - v_policy.allow_past_entry_days) THEN
            RAISE EXCEPTION 'PAST_ENTRY_NOT_ALLOWED: Entry date is beyond the allowed past entry window (% days)', v_policy.allow_past_entry_days;
        END IF;

        IF COALESCE(v_policy.require_task_link, false) AND p_task_id IS NULL AND p_entry_type = 'task' THEN
            RAISE EXCEPTION 'TASK_LINK_REQUIRED: Task selection is required by organization policy';
        END IF;
    END IF;

    -- Auto-detect existing entry for same board, task, date, entry_type if p_entry_id is NULL
    IF p_entry_id IS NULL THEN
        SELECT id INTO p_entry_id
        FROM timesheet_entries
        WHERE timesheet_id = p_timesheet_id
          AND ((p_board_id IS NULL AND board_id IS NULL) OR (p_board_id IS NOT NULL AND (board_id::text = p_board_id::text OR board_id::text = LTRIM(RIGHT(p_board_id::text, 12), '0') OR p_board_id::text = LTRIM(RIGHT(board_id::text, 12), '0'))))
          AND ((p_task_id IS NULL AND task_id IS NULL) OR (p_task_id IS NOT NULL AND (task_id::text = p_task_id::text OR task_id::text = LTRIM(RIGHT(p_task_id::text, 12), '0') OR p_task_id::text = LTRIM(RIGHT(task_id::text, 12), '0'))))
          AND entry_date = p_entry_date
          AND entry_type = p_entry_type
        LIMIT 1;
    END IF;

    -- If hours <= 0, delete entry if present
    IF p_hours <= 0 THEN
        IF p_entry_id IS NOT NULL THEN
            DELETE FROM timesheet_entries WHERE id = p_entry_id AND timesheet_id = p_timesheet_id;
            UPDATE timesheets
            SET total_hours = (SELECT COALESCE(SUM(hours), 0.00) FROM timesheet_entries WHERE timesheet_id = p_timesheet_id),
                updated_at = NOW()
            WHERE id = p_timesheet_id;
        END IF;
        RETURN;
    END IF;

    -- Calculate daily hours total for overtime evaluation
    SELECT COALESCE(SUM(hours), 0.00) INTO v_existing_day_hours
    FROM timesheet_entries
    WHERE user_id = p_user_id
      AND entry_date = p_entry_date
      AND (p_entry_id IS NULL OR id != p_entry_id);

    v_new_day_hours := v_existing_day_hours + p_hours;

    IF v_policy IS NOT NULL AND v_policy.max_hours_per_day IS NOT NULL AND v_new_day_hours > v_policy.max_hours_per_day THEN
        IF v_policy.overtime_policy = 'block_submission' THEN
            RAISE EXCEPTION 'OVERTIME_BLOCKED: Total hours for % (%) exceeds maximum daily limit (%)', p_entry_date, v_new_day_hours, v_policy.max_hours_per_day;
        ELSIF v_policy.overtime_policy = 'flag_only' THEN
            v_is_overtime := true;
        END IF;
    END IF;

    -- Upsert entry record
    IF p_entry_id IS NOT NULL THEN
        UPDATE timesheet_entries SET
            board_id = p_board_id,
            task_id = p_task_id,
            entry_date = p_entry_date,
            hours = p_hours,
            entry_type = p_entry_type,
            description = p_description,
            is_overtime = v_is_overtime,
            updated_at = NOW()
        WHERE id = p_entry_id AND timesheet_id = p_timesheet_id
        RETURNING * INTO v_result_entry;
    ELSE
        INSERT INTO timesheet_entries (
            timesheet_id, user_id, board_id, task_id, entry_date, hours, entry_type, description, is_overtime
        ) VALUES (
            p_timesheet_id, p_user_id, p_board_id, p_task_id, p_entry_date, p_hours, p_entry_type, p_description, v_is_overtime
        )
        RETURNING * INTO v_result_entry;
    END IF;

    -- Recalculate parent timesheet total_hours
    UPDATE timesheets
    SET total_hours = (SELECT COALESCE(SUM(hours), 0.00) FROM timesheet_entries WHERE timesheet_id = p_timesheet_id),
        updated_at = NOW()
    WHERE id = p_timesheet_id;

    RETURN NEXT v_result_entry;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
