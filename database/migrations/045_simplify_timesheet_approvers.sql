-- 045_simplify_timesheet_approvers.sql
-- Simplify Timesheet Approver Assignments to Global Organization Level

DO $$
BEGIN
    -- Drop old board index & constraint if present
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_timesheet_approver_org_board_user'
    ) THEN
        ALTER TABLE timesheet_approver_assignments DROP CONSTRAINT uq_timesheet_approver_org_board_user;
    END IF;
END $$;

DROP INDEX IF EXISTS idx_timesheet_approver_assignments_org_board;

-- Clean up duplicate rows per (org_id, approver_user_id) before dropping column
DELETE FROM timesheet_approver_assignments a
USING timesheet_approver_assignments b
WHERE a.ctid < b.ctid
  AND a.org_id = b.org_id
  AND a.approver_user_id = b.approver_user_id;

-- Remove board_id column if present
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'timesheet_approver_assignments' AND column_name = 'board_id'
    ) THEN
        ALTER TABLE timesheet_approver_assignments DROP COLUMN board_id;
    END IF;
END $$;

-- Add new unique constraint for org_id and approver_user_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_timesheet_approver_org_user'
    ) THEN
        ALTER TABLE timesheet_approver_assignments 
        ADD CONSTRAINT uq_timesheet_approver_org_user UNIQUE (org_id, approver_user_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_timesheet_approver_assignments_org_user 
ON timesheet_approver_assignments(org_id, approver_user_id) WHERE is_active = true;
