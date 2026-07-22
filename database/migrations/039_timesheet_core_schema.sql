-- 039_timesheet_core_schema.sql
-- Enterprise Timesheet Core Tables: Header, Daily Entries, and Audit Log

CREATE TABLE IF NOT EXISTS timesheets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    user_id UUID NOT NULL,
    week_start_date DATE NOT NULL,
    week_end_date DATE NOT NULL,
    status timesheet_status NOT NULL DEFAULT 'draft',
    total_hours NUMERIC(6,2) NOT NULL DEFAULT 0.00,
    submitted_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,
    approver_id UUID NULL,
    approver_comment TEXT,
    member_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_timesheet_org_user_week UNIQUE (org_id, user_id, week_start_date)
);

CREATE TABLE IF NOT EXISTS timesheet_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timesheet_id UUID NOT NULL REFERENCES timesheets(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    board_id UUID NULL,
    task_id UUID NULL,
    entry_date DATE NOT NULL,
    hours NUMERIC(4,2) NOT NULL CHECK (hours > 0 AND hours <= 24),
    entry_type timesheet_entry_type NOT NULL DEFAULT 'task',
    description TEXT,
    is_overtime BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS timesheet_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timesheet_id UUID NOT NULL REFERENCES timesheets(id) ON DELETE CASCADE,
    actor_user_id UUID NOT NULL,
    from_status timesheet_status,
    to_status timesheet_status NOT NULL,
    comment TEXT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
