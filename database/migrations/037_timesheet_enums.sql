-- 037_timesheet_enums.sql
-- Enterprise Timesheet System Enums

DO $$ BEGIN
    CREATE TYPE timesheet_status AS ENUM ('draft', 'submitted', 'approved', 'rejected', 'recalled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE timesheet_entry_type AS ENUM ('task', 'meeting', 'general', 'leave', 'holiday');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE week_start_day AS ENUM ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE overtime_policy AS ENUM ('none', 'flag_only', 'block_submission');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;
