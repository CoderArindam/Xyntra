-- 030_activity_logging_enhancements.sql
-- Add PRIORITY_CHANGED, TITLE_CHANGED, DESCRIPTION_CHANGED to activity_type_enum
-- Update generate_task_activity() trigger function and generate_notifications() trigger function

-- 1. Alter activity_type_enum to include missing change types
ALTER TYPE activity_type_enum ADD VALUE IF NOT EXISTS 'PRIORITY_CHANGED';
ALTER TYPE activity_type_enum ADD VALUE IF NOT EXISTS 'TITLE_CHANGED';
ALTER TYPE activity_type_enum ADD VALUE IF NOT EXISTS 'DESCRIPTION_CHANGED';

-- 2. Enhance Activity Generation Trigger Function for Tasks
CREATE OR REPLACE FUNCTION generate_task_activity()
RETURNS TRIGGER AS $$
DECLARE
    v_org_id INTEGER;
    v_actor_id INTEGER;
    v_setting TEXT;
    v_old_column_name VARCHAR;
    v_new_column_name VARCHAR;
    v_old_assignee_name VARCHAR;
    v_new_assignee_name VARCHAR;
BEGIN
    -- Get org ID
    SELECT organization_id INTO v_org_id FROM boards WHERE id = COALESCE(NEW.board_id, OLD.board_id);
    
    -- Actor ID safely parsed from session setting
    v_setting := current_setting('app.current_user_id', true);
    IF v_setting IS NOT NULL AND v_setting != '' THEN
        v_actor_id := v_setting::INTEGER;
    END IF;

    IF TG_OP = 'INSERT' THEN
        INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, old_value, new_value)
        VALUES (v_org_id, 'TASK', NEW.id, COALESCE(v_actor_id, NEW.created_by), 'CREATED', NULL, jsonb_build_object('title', NEW.title));
    
    ELSIF TG_OP = 'UPDATE' THEN
        -- Status / Column change
        IF NEW.column_id IS DISTINCT FROM OLD.column_id THEN
            SELECT name INTO v_old_column_name FROM board_columns WHERE id = OLD.column_id;
            SELECT name INTO v_new_column_name FROM board_columns WHERE id = NEW.column_id;
            INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, old_value, new_value)
            VALUES (
                v_org_id, 'TASK', NEW.id, v_actor_id, 'STATUS_CHANGED', 
                jsonb_build_object('column_id', OLD.column_id, 'column_name', v_old_column_name), 
                jsonb_build_object('column_id', NEW.column_id, 'column_name', v_new_column_name)
            );
        END IF;

        -- Assignee change
        IF NEW.assigned_to IS DISTINCT FROM OLD.assigned_to THEN
            IF OLD.assigned_to IS NOT NULL THEN
                SELECT COALESCE(NULLIF(TRIM(CONCAT(first_name, ' ', last_name)), ''), email) 
                INTO v_old_assignee_name FROM users WHERE id = OLD.assigned_to;
            END IF;
            IF NEW.assigned_to IS NOT NULL THEN
                SELECT COALESCE(NULLIF(TRIM(CONCAT(first_name, ' ', last_name)), ''), email) 
                INTO v_new_assignee_name FROM users WHERE id = NEW.assigned_to;
            END IF;
            INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, old_value, new_value)
            VALUES (
                v_org_id, 'TASK', NEW.id, v_actor_id, 'ASSIGNEE_CHANGED', 
                jsonb_build_object('assigned_to', OLD.assigned_to, 'assignee_name', v_old_assignee_name), 
                jsonb_build_object('assigned_to', NEW.assigned_to, 'assignee_name', v_new_assignee_name)
            );
        END IF;

        -- Priority change
        IF NEW.priority IS DISTINCT FROM OLD.priority THEN
            INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, old_value, new_value)
            VALUES (
                v_org_id, 'TASK', NEW.id, v_actor_id, 'PRIORITY_CHANGED', 
                jsonb_build_object('priority', OLD.priority), 
                jsonb_build_object('priority', NEW.priority)
            );
        END IF;

        -- Due Date change
        IF NEW.due_date IS DISTINCT FROM OLD.due_date THEN
            INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, old_value, new_value)
            VALUES (
                v_org_id, 'TASK', NEW.id, v_actor_id, 'DUE_DATE_CHANGED', 
                jsonb_build_object('due_date', OLD.due_date), 
                jsonb_build_object('due_date', NEW.due_date)
            );
        END IF;

        -- Title change
        IF NEW.title IS DISTINCT FROM OLD.title THEN
            INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, old_value, new_value)
            VALUES (
                v_org_id, 'TASK', NEW.id, v_actor_id, 'TITLE_CHANGED', 
                jsonb_build_object('title', OLD.title), 
                jsonb_build_object('title', NEW.title)
            );
        END IF;

        -- Description change
        IF NEW.description IS DISTINCT FROM OLD.description THEN
            INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, old_value, new_value)
            VALUES (
                v_org_id, 'TASK', NEW.id, v_actor_id, 'DESCRIPTION_CHANGED', 
                jsonb_build_object('description', OLD.description), 
                jsonb_build_object('description', NEW.description)
            );
        END IF;
    END IF;

    RETURN NULL; 
END;
$$ LANGUAGE plpgsql;

-- 3. Enhance Notification Generation Trigger Function
CREATE OR REPLACE FUNCTION generate_notifications()
RETURNS TRIGGER AS $$
DECLARE
    v_task_record RECORD;
    v_old_assignee INTEGER;
    v_new_assignee INTEGER;
BEGIN
    IF NEW.entity_type IN ('TASK', 'COMMENT') THEN
        SELECT assigned_to INTO v_task_record FROM tasks WHERE id = NEW.entity_id;

        IF NEW.activity_type = 'ASSIGNEE_CHANGED' THEN
            v_old_assignee := (NEW.old_value->>'assigned_to')::INTEGER;
            v_new_assignee := (NEW.new_value->>'assigned_to')::INTEGER;
            
            IF v_old_assignee IS NOT NULL AND v_old_assignee != COALESCE(NEW.user_id, -1) THEN
                INSERT INTO notifications (user_id, activity_id) VALUES (v_old_assignee, NEW.id);
            END IF;

            IF v_new_assignee IS NOT NULL AND v_new_assignee != COALESCE(NEW.user_id, -1) THEN
                INSERT INTO notifications (user_id, activity_id) VALUES (v_new_assignee, NEW.id);
            END IF;

        ELSIF NEW.activity_type IN ('DUE_DATE_CHANGED', 'STATUS_CHANGED', 'COMMENT_ADDED', 'PRIORITY_CHANGED', 'TITLE_CHANGED', 'DESCRIPTION_CHANGED') THEN
            IF v_task_record.assigned_to IS NOT NULL AND v_task_record.assigned_to != COALESCE(NEW.user_id, -1) THEN
                INSERT INTO notifications (user_id, activity_id) VALUES (v_task_record.assigned_to, NEW.id);
            END IF;
        END IF;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
