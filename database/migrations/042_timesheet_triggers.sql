-- 042_timesheet_triggers.sql
-- Enterprise Timesheet System Triggers

-- 1. updated_at timestamp function
CREATE OR REPLACE FUNCTION update_timesheet_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. updated_at triggers
DROP TRIGGER IF EXISTS trg_update_timesheet_policies_timestamp ON timesheet_policies;
CREATE TRIGGER trg_update_timesheet_policies_timestamp
BEFORE UPDATE ON timesheet_policies
FOR EACH ROW EXECUTE FUNCTION update_timesheet_timestamp();

DROP TRIGGER IF EXISTS trg_update_timesheets_timestamp ON timesheets;
CREATE TRIGGER trg_update_timesheets_timestamp
BEFORE UPDATE ON timesheets
FOR EACH ROW EXECUTE FUNCTION update_timesheet_timestamp();

DROP TRIGGER IF EXISTS trg_update_timesheet_entries_timestamp ON timesheet_entries;
CREATE TRIGGER trg_update_timesheet_entries_timestamp
BEFORE UPDATE ON timesheet_entries
FOR EACH ROW EXECUTE FUNCTION update_timesheet_timestamp();

-- 3. Trigger for automatically recalculating timesheets.total_hours after entry changes
CREATE OR REPLACE FUNCTION recalculate_timesheet_total_hours()
RETURNS TRIGGER AS $$
DECLARE
    v_target_id UUID;
BEGIN
    v_target_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.timesheet_id ELSE NEW.timesheet_id END;
    UPDATE timesheets
    SET total_hours = (SELECT COALESCE(SUM(hours), 0.00) FROM timesheet_entries WHERE timesheet_id = v_target_id),
        updated_at = NOW()
    WHERE id = v_target_id;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_recalculate_timesheet_total_hours ON timesheet_entries;
CREATE TRIGGER trg_recalculate_timesheet_total_hours
AFTER INSERT OR UPDATE OR DELETE ON timesheet_entries
FOR EACH ROW EXECUTE FUNCTION recalculate_timesheet_total_hours();
