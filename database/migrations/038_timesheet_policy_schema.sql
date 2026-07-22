-- 038_timesheet_policy_schema.sql
-- Enterprise Timesheet System Policy and Approver Assignment Tables

CREATE TABLE IF NOT EXISTS timesheet_policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL UNIQUE,
    week_start_day week_start_day NOT NULL DEFAULT 'monday',
    standard_hours_per_day NUMERIC(4,2) NOT NULL DEFAULT 8.00,
    standard_hours_per_week NUMERIC(5,2) NOT NULL DEFAULT 40.00,
    max_hours_per_day NUMERIC(4,2) DEFAULT 12.00,
    overtime_policy overtime_policy NOT NULL DEFAULT 'flag_only',
    submission_deadline_days INTEGER DEFAULT 2,
    allow_future_entry BOOLEAN DEFAULT false,
    allow_past_entry_days INTEGER DEFAULT 30,
    require_task_link BOOLEAN DEFAULT false,
    allow_member_recall BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS timesheet_approver_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    board_id UUID NULL,
    approver_user_id UUID NOT NULL,
    assigned_by UUID NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_timesheet_approver_org_board_user UNIQUE (org_id, board_id, approver_user_id)
);
