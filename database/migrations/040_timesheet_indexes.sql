-- 040_timesheet_indexes.sql
-- Enterprise Timesheet Indexes

CREATE INDEX IF NOT EXISTS idx_timesheets_org_user_week ON timesheets(org_id, user_id, week_start_date);
CREATE INDEX IF NOT EXISTS idx_timesheets_org_status ON timesheets(org_id, status);
CREATE INDEX IF NOT EXISTS idx_timesheets_approver_status ON timesheets(approver_id, status) WHERE approver_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_timesheet_entries_timesheet_id ON timesheet_entries(timesheet_id);
CREATE INDEX IF NOT EXISTS idx_timesheet_entries_user_date ON timesheet_entries(user_id, entry_date);
CREATE INDEX IF NOT EXISTS idx_timesheet_entries_board_id ON timesheet_entries(board_id) WHERE board_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_timesheet_entries_task_id ON timesheet_entries(task_id) WHERE task_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_timesheet_audit_log_timesheet_id ON timesheet_audit_log(timesheet_id);
CREATE INDEX IF NOT EXISTS idx_timesheet_approver_assignments_org_board ON timesheet_approver_assignments(org_id, board_id);
