-- 007_triggers.sql
-- Automated event pipeline, sequences, and timestamps

-- 1. Updated At Trigger
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tasks_updated_at
BEFORE UPDATE ON tasks
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 2. Project Sequence ID Generator
CREATE OR REPLACE FUNCTION set_project_sequence_id()
RETURNS TRIGGER AS $$
DECLARE
    v_next_seq INTEGER;
BEGIN
    -- Using COALESCE to handle the first task case
    -- A gapless sequence isn't strictly required, but this avoids needing a dedicated sequences table
    SELECT COALESCE(MAX(project_sequence_id), 0) + 1 INTO v_next_seq
    FROM tasks
    WHERE board_id = NEW.board_id;
    
    NEW.project_sequence_id = v_next_seq;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_set_project_sequence_id
BEFORE INSERT ON tasks
FOR EACH ROW EXECUTE FUNCTION set_project_sequence_id();


-- 3. Completed At Logic
CREATE OR REPLACE FUNCTION sync_completed_at()
RETURNS TRIGGER AS $$
DECLARE
    v_column_type column_type_enum;
BEGIN
    SELECT column_type INTO v_column_type
    FROM board_columns
    WHERE id = NEW.column_id;

    IF v_column_type = 'DONE' THEN
        IF NEW.completed_at IS NULL THEN
            NEW.completed_at = CURRENT_TIMESTAMP;
        END IF;
    ELSE
        NEW.completed_at = NULL;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tasks_completed_at
BEFORE INSERT OR UPDATE OF column_id ON tasks
FOR EACH ROW EXECUTE FUNCTION sync_completed_at();


-- 4. Default Board Columns & Owner Assignment
CREATE OR REPLACE FUNCTION initialize_new_board()
RETURNS TRIGGER AS $$
BEGIN
    -- Assign owner
    IF NEW.owner_id IS NOT NULL THEN
        INSERT INTO board_members (board_id, user_id, permission)
        VALUES (NEW.id, NEW.owner_id, 'OWNER');
    END IF;

    -- Create default columns
    INSERT INTO board_columns (board_id, name, position, column_type) VALUES
    (NEW.id, 'To Do', 1, 'TODO'),
    (NEW.id, 'In Progress', 2, 'IN_PROGRESS'),
    (NEW.id, 'Done', 3, 'DONE');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_initialize_new_board
AFTER INSERT ON boards
FOR EACH ROW EXECUTE FUNCTION initialize_new_board();


-- 5. Activity Generation (Event Pipeline - Tasks)
CREATE OR REPLACE FUNCTION generate_task_activity()
RETURNS TRIGGER AS $$
DECLARE
    v_org_id INTEGER;
    v_actor_id INTEGER;
BEGIN
    -- Get org ID
    SELECT organization_id INTO v_org_id FROM boards WHERE id = COALESCE(NEW.board_id, OLD.board_id);
    
    -- In a real app, actor_id comes from a session variable set by the backend, or we assume updated_by/created_by
    -- Since we don't have updated_by on tasks yet, we can use created_by for inserts, or assume the backend passes it.
    -- To keep it simple, we use a custom GUC variable that the backend sets before mutation:
    -- SET LOCAL request.jwt.claim.user_id = '123';
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
    END IF;

    RETURN NULL; -- AFTER triggers can return NULL
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_generate_task_activity
AFTER INSERT OR UPDATE ON tasks
FOR EACH ROW EXECUTE FUNCTION generate_task_activity();


-- 6. Notification Generation (Event Pipeline - Activities -> Notifications)
CREATE OR REPLACE FUNCTION generate_notifications()
RETURNS TRIGGER AS $$
DECLARE
    v_task_record RECORD;
BEGIN
    -- If this is a task activity, alert the assignee
    IF NEW.entity_type = 'TASK' THEN
        SELECT assigned_to INTO v_task_record FROM tasks WHERE id = NEW.entity_id;
        
        -- Don't notify the person who caused the activity, only if they are assigned
        IF v_task_record.assigned_to IS NOT NULL AND v_task_record.assigned_to != COALESCE(NEW.user_id, -1) THEN
            INSERT INTO notifications (user_id, activity_id)
            VALUES (v_task_record.assigned_to, NEW.id);
        END IF;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_generate_notifications
AFTER INSERT ON activities
FOR EACH ROW EXECUTE FUNCTION generate_notifications();
