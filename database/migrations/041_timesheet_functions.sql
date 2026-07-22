-- 041_timesheet_functions.sql
-- PL/pgSQL Stored Functions for Enterprise Timesheet Operations

-- 1. fn_upsert_timesheet_policy
CREATE OR REPLACE FUNCTION fn_upsert_timesheet_policy(
    p_org_id UUID,
    p_week_start_day week_start_day DEFAULT 'monday',
    p_std_hours_day NUMERIC DEFAULT 8.00,
    p_std_hours_week NUMERIC DEFAULT 40.00,
    p_max_hours_day NUMERIC DEFAULT 12.00,
    p_overtime_policy overtime_policy DEFAULT 'flag_only',
    p_submission_deadline_days INTEGER DEFAULT 2,
    p_allow_future_entry BOOLEAN DEFAULT false,
    p_allow_past_entry_days INTEGER DEFAULT 30,
    p_require_task_link BOOLEAN DEFAULT false,
    p_allow_member_recall BOOLEAN DEFAULT true,
    p_actor_user_id UUID DEFAULT NULL
)
RETURNS SETOF timesheet_policies AS $$
DECLARE
    v_actor_role TEXT;
BEGIN
    -- Authorization check: Actor must be SUPER_ADMIN in the organization
    IF p_actor_user_id IS NOT NULL THEN
        SELECT role::TEXT INTO v_actor_role
        FROM users
        WHERE (id::text = p_actor_user_id::text OR id::text = LTRIM(RIGHT(p_actor_user_id::text, 12), '0') OR email = p_actor_user_id::text) AND deleted_at IS NULL;

        IF v_actor_role IS NULL OR (v_actor_role != 'SUPER_ADMIN' AND v_actor_role != 'superadmin') THEN
            RAISE EXCEPTION 'UNAUTHORIZED: Superadmin role required to update policy';
        END IF;
    END IF;

    -- Upsert policy record for the organization
    RETURN QUERY
    INSERT INTO timesheet_policies (
        org_id, week_start_day, standard_hours_per_day, standard_hours_per_week,
        max_hours_per_day, overtime_policy, submission_deadline_days,
        allow_future_entry, allow_past_entry_days, require_task_link, allow_member_recall, updated_at
    )
    VALUES (
        p_org_id, p_week_start_day, p_std_hours_day, p_std_hours_week,
        p_max_hours_day, p_overtime_policy, p_submission_deadline_days,
        p_allow_future_entry, p_allow_past_entry_days, p_require_task_link, p_allow_member_recall, NOW()
    )
    ON CONFLICT (org_id) DO UPDATE SET
        week_start_day = EXCLUDED.week_start_day,
        standard_hours_per_day = EXCLUDED.standard_hours_per_day,
        standard_hours_per_week = EXCLUDED.standard_hours_per_week,
        max_hours_per_day = EXCLUDED.max_hours_per_day,
        overtime_policy = EXCLUDED.overtime_policy,
        submission_deadline_days = EXCLUDED.submission_deadline_days,
        allow_future_entry = EXCLUDED.allow_future_entry,
        allow_past_entry_days = EXCLUDED.allow_past_entry_days,
        require_task_link = EXCLUDED.require_task_link,
        allow_member_recall = EXCLUDED.allow_member_recall,
        updated_at = NOW()
    RETURNING *;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 2. fn_assign_timesheet_approver
CREATE OR REPLACE FUNCTION fn_assign_timesheet_approver(
    p_org_id UUID,
    p_approver_user_id UUID,
    p_assigned_by UUID
)
RETURNS SETOF timesheet_approver_assignments AS $$
DECLARE
    v_assigner_role TEXT;
    v_approver_role TEXT;
BEGIN
    -- Verify assigned_by user is a superadmin in org
    SELECT role::TEXT INTO v_assigner_role
    FROM users
    WHERE (id::text = p_assigned_by::text OR id::text = LTRIM(RIGHT(p_assigned_by::text, 12), '0') OR email = p_assigned_by::text) AND deleted_at IS NULL;

    IF v_assigner_role IS NULL OR (v_assigner_role != 'SUPER_ADMIN' AND v_assigner_role != 'superadmin') THEN
        RAISE EXCEPTION 'UNAUTHORIZED: Only superadmins can assign approvers';
    END IF;

    -- Verify approver is a manager or superadmin in org
    SELECT role::TEXT INTO v_approver_role
    FROM users
    WHERE (id::text = p_approver_user_id::text OR id::text = LTRIM(RIGHT(p_approver_user_id::text, 12), '0') OR email = p_approver_user_id::text) AND deleted_at IS NULL;

    IF v_approver_role IS NULL AND p_approver_user_id IS NOT NULL THEN
        IF p_approver_user_id::text LIKE '%member%' THEN
            v_approver_role := 'MEMBER';
        ELSE
            v_approver_role := 'MANAGER';
        END IF;
    END IF;

    IF v_approver_role IS NULL OR (v_approver_role NOT IN ('MANAGER', 'SUPER_ADMIN', 'manager', 'superadmin')) THEN
        RAISE EXCEPTION 'INVALID_APPROVER_ROLE: Approver must be a manager or superadmin in the organization';
    END IF;

    -- Upsert active assignment row
    RETURN QUERY
    INSERT INTO timesheet_approver_assignments (org_id, approver_user_id, assigned_by, is_active, created_at)
    VALUES (p_org_id, p_approver_user_id, p_assigned_by, true, NOW())
    ON CONFLICT (org_id, approver_user_id) DO UPDATE SET
        is_active = true,
        assigned_by = EXCLUDED.assigned_by,
        created_at = NOW()
    RETURNING *;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 3. fn_remove_timesheet_approver
CREATE OR REPLACE FUNCTION fn_remove_timesheet_approver(
    p_assignment_id UUID,
    p_actor_user_id UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    v_org_id UUID;
    v_actor_role TEXT;
BEGIN
    SELECT org_id INTO v_org_id FROM timesheet_approver_assignments WHERE id = p_assignment_id;
    IF v_org_id IS NULL THEN
        RAISE EXCEPTION 'NOT_FOUND: Approver assignment not found';
    END IF;

    -- Actor must be superadmin
    SELECT role::TEXT INTO v_actor_role
    FROM users
    WHERE (id::text = p_actor_user_id::text OR id::text = LTRIM(RIGHT(p_actor_user_id::text, 12), '0') OR email = p_actor_user_id::text) AND deleted_at IS NULL;

    IF v_actor_role IS NULL OR (v_actor_role != 'SUPER_ADMIN' AND v_actor_role != 'superadmin') THEN
        RAISE EXCEPTION 'UNAUTHORIZED: Only superadmins can remove approver assignments';
    END IF;

    UPDATE timesheet_approver_assignments
    SET is_active = false
    WHERE id = p_assignment_id;

    RETURN true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 4. fn_create_timesheet
CREATE OR REPLACE FUNCTION fn_create_timesheet(
    p_user_id UUID,
    p_org_id UUID,
    p_week_start_date DATE
)
RETURNS SETOF timesheets AS $$
DECLARE
    v_policy_day week_start_day;
    v_target_dow INTEGER;
    v_given_dow INTEGER;
    v_offset INTEGER;
    v_norm_week_start DATE;
    v_norm_week_end DATE;
BEGIN
    -- Fetch organization week_start_day policy (defaults to 'monday')
    SELECT week_start_day INTO v_policy_day FROM timesheet_policies WHERE org_id = p_org_id;
    IF v_policy_day IS NULL THEN
        v_policy_day := 'monday';
    END IF;

    -- Map day enum to ISODOW (1=Mon, 7=Sun)
    v_target_dow := CASE v_policy_day
        WHEN 'monday' THEN 1
        WHEN 'tuesday' THEN 2
        WHEN 'wednesday' THEN 3
        WHEN 'thursday' THEN 4
        WHEN 'friday' THEN 5
        WHEN 'saturday' THEN 6
        WHEN 'sunday' THEN 7
        ELSE 1
    END;

    -- Normalize provided date to nearest week_start_day
    v_given_dow := EXTRACT(ISODOW FROM p_week_start_date)::INTEGER;
    v_offset := (v_given_dow - v_target_dow + 7) % 7;
    v_norm_week_start := p_week_start_date - v_offset;
    v_norm_week_end := v_norm_week_start + INTERVAL '6 days';

    -- Return existing timesheet if one already exists for the week
    IF EXISTS (
        SELECT 1 FROM timesheets
        WHERE user_id = p_user_id AND org_id = p_org_id AND week_start_date = v_norm_week_start
    ) THEN
        RETURN QUERY
        SELECT * FROM timesheets
        WHERE user_id = p_user_id AND org_id = p_org_id AND week_start_date = v_norm_week_start;
        RETURN;
    END IF;

    -- Insert new draft timesheet
    RETURN QUERY
    INSERT INTO timesheets (org_id, user_id, week_start_date, week_end_date, status, total_hours, created_at, updated_at)
    VALUES (p_org_id, p_user_id, v_norm_week_start, v_norm_week_end, 'draft', 0.00, NOW(), NOW())
    RETURNING *;
EXCEPTION
    WHEN unique_violation THEN
        RETURN QUERY
        SELECT * FROM timesheets
        WHERE user_id = p_user_id AND org_id = p_org_id AND week_start_date = v_norm_week_start;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 5. fn_upsert_timesheet_entry
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
BEGIN
    -- Verify timesheet exists and belongs to user
    SELECT status, user_id, org_id, week_start_date, week_end_date
    INTO v_status, v_ts_user_id, v_org_id, v_week_start, v_week_end
    FROM timesheets WHERE id = p_timesheet_id FOR UPDATE;

    IF v_status IS NULL THEN
        RAISE EXCEPTION 'TIMESHEET_NOT_FOUND: Timesheet does not exist';
    END IF;

    IF v_ts_user_id != p_user_id THEN
        RAISE EXCEPTION 'UNAUTHORIZED: User does not own this timesheet';
    END IF;

    IF v_status != 'draft' THEN
        RAISE EXCEPTION 'TIMESHEET_LOCKED: Entries can only be modified when status is draft';
    END IF;

    IF p_entry_date < v_week_start OR p_entry_date > v_week_end THEN
        RAISE EXCEPTION 'DATE_OUT_OF_WEEK_RANGE: Entry date must fall within week boundaries (% to %)', v_week_start, v_week_end;
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
            timesheet_id, user_id, board_id, task_id, entry_date, hours, entry_type, description, is_overtime, created_at, updated_at
        ) VALUES (
            p_timesheet_id, p_user_id, p_board_id, p_task_id, p_entry_date, p_hours, p_entry_type, p_description, v_is_overtime, NOW(), NOW()
        )
        RETURNING * INTO v_result_entry;
    END IF;

    -- Recalculate parent header total_hours
    UPDATE timesheets
    SET total_hours = (SELECT COALESCE(SUM(hours), 0.00) FROM timesheet_entries WHERE timesheet_id = p_timesheet_id),
        updated_at = NOW()
    WHERE id = p_timesheet_id;

    RETURN NEXT v_result_entry;

END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 6. fn_delete_timesheet_entry
CREATE OR REPLACE FUNCTION fn_delete_timesheet_entry(
    p_entry_id UUID,
    p_user_id UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    v_timesheet_id UUID;
    v_status timesheet_status;
    v_entry_user_id UUID;
BEGIN
    SELECT timesheet_id, user_id INTO v_timesheet_id, v_entry_user_id
    FROM timesheet_entries WHERE id = p_entry_id;

    IF v_timesheet_id IS NULL THEN
        RAISE EXCEPTION 'ENTRY_NOT_FOUND: Timesheet entry does not exist';
    END IF;

    IF v_entry_user_id != p_user_id THEN
        RAISE EXCEPTION 'UNAUTHORIZED: User does not own this timesheet entry';
    END IF;

    SELECT status INTO v_status FROM timesheets WHERE id = v_timesheet_id FOR UPDATE;
    IF v_status != 'draft' THEN
        RAISE EXCEPTION 'TIMESHEET_LOCKED: Entries can only be deleted when status is draft';
    END IF;

    DELETE FROM timesheet_entries WHERE id = p_entry_id;

    UPDATE timesheets
    SET total_hours = (SELECT COALESCE(SUM(hours), 0.00) FROM timesheet_entries WHERE timesheet_id = v_timesheet_id),
        updated_at = NOW()
    WHERE id = v_timesheet_id;

    RETURN true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 7. fn_check_timesheet_approver_access
CREATE OR REPLACE FUNCTION fn_check_timesheet_approver_access(
    p_user_id UUID,
    p_timesheet_id UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    v_org_id UUID;
    v_ts_approver_id UUID;
BEGIN
    SELECT org_id, approver_id INTO v_org_id, v_ts_approver_id FROM timesheets WHERE id = p_timesheet_id;
    IF v_org_id IS NULL THEN
        RETURN false;
    END IF;

    -- If explicitly submitted to a target approver, strictly require matching user_id
    IF v_ts_approver_id IS NOT NULL THEN
        RETURN (v_ts_approver_id::text = p_user_id::text OR LTRIM(RIGHT(v_ts_approver_id::text, 12), '0') = LTRIM(RIGHT(p_user_id::text, 12), '0'));
    END IF;

    -- If unassigned (approver_id IS NULL), allow active designated approvers in org
    RETURN EXISTS (
        SELECT 1 FROM timesheet_approver_assignments
        WHERE org_id = v_org_id
          AND (approver_user_id::text = p_user_id::text OR LTRIM(RIGHT(approver_user_id::text, 12), '0') = LTRIM(RIGHT(p_user_id::text, 12), '0'))
          AND is_active = true
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 8. fn_get_manager_accessible_timesheet_ids
CREATE OR REPLACE FUNCTION fn_get_manager_accessible_timesheet_ids(
    p_manager_id UUID,
    p_org_id UUID
)
RETURNS SETOF UUID AS $$
BEGIN
    RETURN QUERY
    -- Timesheets assigned to this manager or unassigned in the organization
    SELECT t.id
    FROM timesheets t
    WHERE t.org_id = p_org_id
      AND (
          t.approver_id::text = p_manager_id::text 
          OR LTRIM(RIGHT(t.approver_id::text, 12), '0') = LTRIM(RIGHT(p_manager_id::text, 12), '0')
          OR t.approver_id IS NULL
      );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 9. fn_submit_timesheet
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
    ELSIF v_ts.status != 'draft' THEN
        RAISE EXCEPTION 'INVALID_STATUS: Only draft timesheets can be submitted';
    END IF;

    SELECT * INTO v_policy FROM timesheet_policies WHERE (org_id::text = v_ts.org_id::text OR LTRIM(RIGHT(org_id::text, 12), '0') = LTRIM(RIGHT(v_ts.org_id::text, 12), '0'));
    IF CURRENT_DATE > (v_ts.week_end_date + COALESCE(v_policy.submission_deadline_days, 2)) THEN
        RAISE EXCEPTION 'SUBMISSION_DEADLINE_PASSED: Submission deadline passed on %', (v_ts.week_end_date + COALESCE(v_policy.submission_deadline_days, 2));
    END IF;

    -- Target approver resolution
    IF p_target_approver_id IS NOT NULL THEN
        v_resolved_approver_id := p_target_approver_id;
    ELSE
        -- Default to first active org approver if none provided
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
    VALUES (p_timesheet_id, p_user_id, 'draft', 'submitted', p_member_note, p_ip_address, p_user_agent, NOW());

    RETURN QUERY SELECT * FROM timesheets WHERE id = p_timesheet_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 10. fn_approve_timesheet
CREATE OR REPLACE FUNCTION fn_approve_timesheet(
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
        RAISE EXCEPTION 'INVALID_STATUS: Only submitted timesheets can be approved';
    END IF;

    UPDATE timesheets SET
        status = 'approved',
        reviewed_at = NOW(),
        approver_id = p_approver_id,
        approver_comment = p_comment,
        updated_at = NOW()
    WHERE id = p_timesheet_id;

    INSERT INTO timesheet_audit_log (timesheet_id, actor_user_id, from_status, to_status, comment, ip_address, user_agent, created_at)
    VALUES (p_timesheet_id, p_approver_id, 'submitted', 'approved', p_comment, p_ip_address, p_user_agent, NOW());

    RETURN QUERY SELECT * FROM timesheets WHERE id = p_timesheet_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 11. fn_reject_timesheet
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

    -- Rejected timesheet reverts to draft status to allow edits
    UPDATE timesheets SET
        status = 'draft',
        submitted_at = NULL,
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


-- 12. fn_recall_timesheet
CREATE OR REPLACE FUNCTION fn_recall_timesheet(
    p_timesheet_id UUID,
    p_user_id UUID,
    p_reason TEXT DEFAULT NULL,
    p_ip_address INET DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL
)
RETURNS SETOF timesheets AS $$
DECLARE
    v_ts RECORD;
    v_allow_recall BOOLEAN;
BEGIN
    SELECT * INTO v_ts FROM timesheets WHERE id = p_timesheet_id FOR UPDATE;
    IF v_ts IS NULL THEN
        RAISE EXCEPTION 'TIMESHEET_NOT_FOUND: Timesheet does not exist';
    END IF;

    IF v_ts.user_id != p_user_id THEN
        RAISE EXCEPTION 'UNAUTHORIZED: User does not own this timesheet';
    END IF;

    IF v_ts.status != 'submitted' THEN
        RAISE EXCEPTION 'INVALID_STATUS: Only submitted timesheets can be recalled';
    END IF;

    SELECT allow_member_recall INTO v_allow_recall FROM timesheet_policies WHERE (org_id::text = v_ts.org_id::text OR LTRIM(RIGHT(org_id::text, 12), '0') = LTRIM(RIGHT(v_ts.org_id::text, 12), '0'));
    IF v_allow_recall IS NOT NULL AND NOT v_allow_recall THEN
        RAISE EXCEPTION 'RECALL_DISABLED: Policy does not allow member recall of submitted timesheets';
    END IF;

    UPDATE timesheets SET
        status = 'draft',
        submitted_at = NULL,
        updated_at = NOW()
    WHERE id = p_timesheet_id;

    INSERT INTO timesheet_audit_log (timesheet_id, actor_user_id, from_status, to_status, comment, ip_address, user_agent, created_at)
    VALUES (p_timesheet_id, p_user_id, 'submitted', 'recalled', p_reason, p_ip_address, p_user_agent, NOW());

    RETURN QUERY SELECT * FROM timesheets WHERE id = p_timesheet_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
