-- 009_seed_data.sql
-- Demo Workspace Generator

DO $$
DECLARE
    v_org_id INTEGER;
    v_admin_id INTEGER;
    v_manager_id INTEGER;
    v_member1_id INTEGER;
    v_member2_id INTEGER;
    v_eng_board_id INTEGER;
    v_mkt_board_id INTEGER;
    v_eng_todo_col INTEGER;
    v_eng_prog_col INTEGER;
    v_eng_done_col INTEGER;
    v_mkt_todo_col INTEGER;
    
    -- bcrypt hash for 'password123'
    v_hash VARCHAR := '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW';
BEGIN
    -- 1. Create Organization
    INSERT INTO organizations (name) VALUES ('DevArc') RETURNING id INTO v_org_id;

    -- 2. Create Users
    INSERT INTO users (organization_id, email, password_hash, first_name, last_name, role)
    VALUES (v_org_id, 'admin@devarc.com', v_hash, 'Alice', 'Admin', 'SUPER_ADMIN')
    RETURNING id INTO v_admin_id;

    INSERT INTO users (organization_id, email, password_hash, first_name, last_name, role)
    VALUES (v_org_id, 'manager@devarc.com', v_hash, 'Bob', 'Manager', 'MANAGER')
    RETURNING id INTO v_manager_id;

    INSERT INTO users (organization_id, email, password_hash, first_name, last_name, role)
    VALUES (v_org_id, 'charlie@devarc.com', v_hash, 'Charlie', 'Member', 'MEMBER')
    RETURNING id INTO v_member1_id;

    INSERT INTO users (organization_id, email, password_hash, first_name, last_name, role)
    VALUES (v_org_id, 'dave@devarc.com', v_hash, 'Dave', 'Member', 'MEMBER')
    RETURNING id INTO v_member2_id;

    -- 3. Create Boards (Triggers will create default columns and add owner as OWNER)
    INSERT INTO boards (organization_id, owner_id, name, project_key)
    VALUES (v_org_id, v_admin_id, 'Engineering', 'ENG')
    RETURNING id INTO v_eng_board_id;

    INSERT INTO boards (organization_id, owner_id, name, project_key)
    VALUES (v_org_id, v_manager_id, 'Marketing', 'MKT')
    RETURNING id INTO v_mkt_board_id;

    -- 4. Assign Board Members
    INSERT INTO board_members (board_id, user_id, permission) VALUES
    (v_eng_board_id, v_manager_id, 'EDITOR'),
    (v_eng_board_id, v_member1_id, 'EDITOR'),
    (v_eng_board_id, v_member2_id, 'VIEWER');

    -- 5. Fetch Column IDs for tasks
    SELECT id INTO v_eng_todo_col FROM board_columns WHERE board_id = v_eng_board_id AND column_type = 'TODO' LIMIT 1;
    SELECT id INTO v_eng_prog_col FROM board_columns WHERE board_id = v_eng_board_id AND column_type = 'IN_PROGRESS' LIMIT 1;
    SELECT id INTO v_eng_done_col FROM board_columns WHERE board_id = v_eng_board_id AND column_type = 'DONE' LIMIT 1;
    SELECT id INTO v_mkt_todo_col FROM board_columns WHERE board_id = v_mkt_board_id AND column_type = 'TODO' LIMIT 1;

    -- 6. Create Tasks (Triggers will generate activities, notifications, and completed_at)
    -- Set the app.current_user_id so triggers attribute the creation to the admin
    PERFORM set_config('app.current_user_id', v_admin_id::TEXT, true);

    INSERT INTO tasks (board_id, column_id, title, description, priority, assigned_to, created_by) VALUES
    (v_eng_board_id, v_eng_todo_col, 'Setup CI/CD Pipeline', 'Migrate to GitHub Actions.', 'High', v_member1_id, v_admin_id),
    (v_eng_board_id, v_eng_todo_col, 'Update dependencies', 'Bump React to 19', 'Medium', v_member2_id, v_admin_id),
    (v_eng_board_id, v_eng_prog_col, 'Refactor Database', 'Implement canonical views and project keys.', 'High', v_member1_id, v_admin_id),
    (v_eng_board_id, v_eng_done_col, 'Create Initial MVP', 'Ship it.', 'High', v_admin_id, v_admin_id);

    PERFORM set_config('app.current_user_id', v_manager_id::TEXT, true);
    
    INSERT INTO tasks (board_id, column_id, title, description, priority, assigned_to, created_by) VALUES
    (v_mkt_board_id, v_mkt_todo_col, 'Launch Campaign', 'Prepare social media posts.', 'Medium', v_manager_id, v_manager_id);

END $$;
