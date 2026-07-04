-- 014_notification_enhancements.sql

-- 1. Enhance Activity Generation to capture DUE_DATE_CHANGED
CREATE OR REPLACE FUNCTION generate_task_activity()
RETURNS TRIGGER AS $$
DECLARE
    v_org_id INTEGER;
    v_actor_id INTEGER;
BEGIN
    SELECT organization_id INTO v_org_id FROM boards WHERE id = COALESCE(NEW.board_id, OLD.board_id);
    
    v_actor_id := current_setting('app.current_user_id', true)::INTEGER;

    IF TG_OP = 'INSERT' THEN
        INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, old_value, new_value)
        VALUES (v_org_id, 'TASK', NEW.id, COALESCE(v_actor_id, NEW.created_by), 'CREATED', NULL, jsonb_build_object('title', NEW.title));
    
    ELSIF TG_OP = 'UPDATE' THEN
        -- Status change
        IF NEW.column_id != OLD.column_id THEN
            INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, old_value, new_value)
            VALUES (v_org_id, 'TASK', NEW.id, v_actor_id, 'STATUS_CHANGED', jsonb_build_object('column_id', OLD.column_id), jsonb_build_object('column_id', NEW.column_id));
        END IF;

        -- Assignee change
        IF NEW.assigned_to IS DISTINCT FROM OLD.assigned_to THEN
            INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, old_value, new_value)
            VALUES (v_org_id, 'TASK', NEW.id, v_actor_id, 'ASSIGNEE_CHANGED', jsonb_build_object('assigned_to', OLD.assigned_to), jsonb_build_object('assigned_to', NEW.assigned_to));
        END IF;

        -- Due Date change
        IF NEW.due_date IS DISTINCT FROM OLD.due_date THEN
            INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, old_value, new_value)
            VALUES (v_org_id, 'TASK', NEW.id, v_actor_id, 'DUE_DATE_CHANGED', jsonb_build_object('due_date', OLD.due_date), jsonb_build_object('due_date', NEW.due_date));
        END IF;
    END IF;

    RETURN NULL; 
END;
$$ LANGUAGE plpgsql;


-- 2. Enhance Notification Generation to handle reassignment, due dates, and comments
CREATE OR REPLACE FUNCTION generate_notifications()
RETURNS TRIGGER AS $$
DECLARE
    v_task_record RECORD;
    v_old_assignee INTEGER;
    v_new_assignee INTEGER;
BEGIN
    -- Only generate notifications if this is a task or comment activity
    IF NEW.entity_type IN ('TASK', 'COMMENT') THEN
        
        -- Get the current state of the task (specifically, who is assigned)
        SELECT assigned_to INTO v_task_record FROM tasks WHERE id = NEW.entity_id;

        -- Handle ASSIGNEE_CHANGED: Notify both old and new assignee
        IF NEW.activity_type = 'ASSIGNEE_CHANGED' THEN
            v_old_assignee := (NEW.old_value->>'assigned_to')::INTEGER;
            v_new_assignee := (NEW.new_value->>'assigned_to')::INTEGER;
            
            -- Notify old assignee if they exist and are not the actor
            IF v_old_assignee IS NOT NULL AND v_old_assignee != COALESCE(NEW.user_id, -1) THEN
                INSERT INTO notifications (user_id, activity_id) VALUES (v_old_assignee, NEW.id);
            END IF;

            -- Notify new assignee if they exist and are not the actor
            IF v_new_assignee IS NOT NULL AND v_new_assignee != COALESCE(NEW.user_id, -1) THEN
                INSERT INTO notifications (user_id, activity_id) VALUES (v_new_assignee, NEW.id);
            END IF;

        -- Handle DUE_DATE_CHANGED, STATUS_CHANGED, COMMENT_ADDED: Notify the current assignee
        ELSIF NEW.activity_type IN ('DUE_DATE_CHANGED', 'STATUS_CHANGED', 'COMMENT_ADDED') THEN
            IF v_task_record.assigned_to IS NOT NULL AND v_task_record.assigned_to != COALESCE(NEW.user_id, -1) THEN
                INSERT INTO notifications (user_id, activity_id) VALUES (v_task_record.assigned_to, NEW.id);
            END IF;
        END IF;
        
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
