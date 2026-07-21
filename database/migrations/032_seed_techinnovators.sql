-- 032_seed_techinnovators.sql
-- Seed real Indian Tech Startup workspace: TechInnovators India

DO $$
DECLARE
    v_org_id INTEGER;
    v_admin_id INTEGER;     -- Rajesh Sharma (Founder & CEO)
    v_priya_id INTEGER;     -- Priya Patel (Tech Lead / Engineering Manager)
    v_rohan_id INTEGER;     -- Rohan Gupta (Senior Backend Engineer)
    v_sneha_id INTEGER;     -- Sneha Reddy (Lead UI/UX Designer)
    v_amit_id INTEGER;      -- Amit Kumar (DevOps & Cloud Architect)
    v_ananya_id INTEGER;    -- Ananya Rao (Fullstack Developer)

    v_pay_board_id INTEGER;
    v_fin_board_id INTEGER;
    v_ai_board_id INTEGER;

    v_pay_todo_col INTEGER;
    v_pay_prog_col INTEGER;
    v_pay_done_col INTEGER;

    v_fin_todo_col INTEGER;
    v_fin_prog_col INTEGER;
    v_fin_done_col INTEGER;

    v_ai_todo_col INTEGER;
    v_ai_prog_col INTEGER;
    v_ai_done_col INTEGER;

    v_task_pay1 INTEGER;
    v_task_pay2 INTEGER;
    v_task_pay3 INTEGER;
    v_task_fin1 INTEGER;
    v_task_fin2 INTEGER;
    v_task_fin3 INTEGER;
    v_task_ai1 INTEGER;

    -- bcrypt hash for 'Password123!'
    v_pwd_hash VARCHAR := '$2b$12$5ZIUXiyEDnVJUWd.qu0/3uGY7tsFX85o.pQi6oOllmXH6radlM5TS';
    v_now TIMESTAMP WITH TIME ZONE := CURRENT_TIMESTAMP;
    v_15d_ago TIMESTAMP WITH TIME ZONE := CURRENT_TIMESTAMP - INTERVAL '15 days';
    v_30d_ago TIMESTAMP WITH TIME ZONE := CURRENT_TIMESTAMP - INTERVAL '30 days';
    v_45d_ago TIMESTAMP WITH TIME ZONE := CURRENT_TIMESTAMP - INTERVAL '45 days';
    v_60d_ago TIMESTAMP WITH TIME ZONE := CURRENT_TIMESTAMP - INTERVAL '60 days';
BEGIN
    -- 1. Create Organization
    INSERT INTO organizations (name, created_at)
    VALUES ('TechInnovators India', v_60d_ago)
    RETURNING id INTO v_org_id;

    -- 2. Create Users
    INSERT INTO users (organization_id, email, password_hash, first_name, last_name, role, is_email_verified, created_at)
    VALUES (v_org_id, 'admin@techinnovators.com', v_pwd_hash, 'Rajesh', 'Sharma', 'SUPER_ADMIN', true, v_60d_ago)
    RETURNING id INTO v_admin_id;

    INSERT INTO users (organization_id, email, password_hash, first_name, last_name, role, is_email_verified, created_at)
    VALUES (v_org_id, 'priya.patel@techinnovators.com', v_pwd_hash, 'Priya', 'Patel', 'MANAGER', true, v_60d_ago)
    RETURNING id INTO v_priya_id;

    INSERT INTO users (organization_id, email, password_hash, first_name, last_name, role, is_email_verified, created_at)
    VALUES (v_org_id, 'rohan.gupta@techinnovators.com', v_pwd_hash, 'Rohan', 'Gupta', 'MEMBER', true, v_45d_ago)
    RETURNING id INTO v_rohan_id;

    INSERT INTO users (organization_id, email, password_hash, first_name, last_name, role, is_email_verified, created_at)
    VALUES (v_org_id, 'sneha.reddy@techinnovators.com', v_pwd_hash, 'Sneha', 'Reddy', 'MEMBER', true, CURRENT_TIMESTAMP - INTERVAL '40 days')
    RETURNING id INTO v_sneha_id;

    INSERT INTO users (organization_id, email, password_hash, first_name, last_name, role, is_email_verified, created_at)
    VALUES (v_org_id, 'amit.kumar@techinnovators.com', v_pwd_hash, 'Amit', 'Kumar', 'MEMBER', true, CURRENT_TIMESTAMP - INTERVAL '35 days')
    RETURNING id INTO v_amit_id;

    INSERT INTO users (organization_id, email, password_hash, first_name, last_name, role, is_email_verified, created_at)
    VALUES (v_org_id, 'ananya.rao@techinnovators.com', v_pwd_hash, 'Ananya', 'Rao', 'MEMBER', true, v_30d_ago)
    RETURNING id INTO v_ananya_id;

    -- 3. Create Boards
    INSERT INTO boards (organization_id, owner_id, name, project_key, created_at)
    VALUES (v_org_id, v_admin_id, 'Razorpay Payment & UPI V2 Sync', 'PAY', v_60d_ago)
    RETURNING id INTO v_pay_board_id;

    INSERT INTO boards (organization_id, owner_id, name, project_key, created_at)
    VALUES (v_org_id, v_priya_id, 'Fintech Platform Core Migration', 'FIN', v_45d_ago)
    RETURNING id INTO v_fin_board_id;

    INSERT INTO boards (organization_id, owner_id, name, project_key, created_at)
    VALUES (v_org_id, v_admin_id, 'AI Co-Pilot & Customer Analytics', 'AI', v_30d_ago)
    RETURNING id INTO v_ai_board_id;

    -- 4. Add Board Memberships
    INSERT INTO board_members (board_id, user_id, permission) VALUES
    (v_pay_board_id, v_priya_id, 'EDITOR'),
    (v_pay_board_id, v_rohan_id, 'EDITOR'),
    (v_pay_board_id, v_amit_id, 'EDITOR'),
    (v_pay_board_id, v_ananya_id, 'EDITOR'),

    (v_fin_board_id, v_admin_id, 'OWNER'),
    (v_fin_board_id, v_rohan_id, 'EDITOR'),
    (v_fin_board_id, v_sneha_id, 'EDITOR'),
    (v_fin_board_id, v_amit_id, 'EDITOR'),
    (v_fin_board_id, v_ananya_id, 'EDITOR'),

    (v_ai_board_id, v_priya_id, 'EDITOR'),
    (v_ai_board_id, v_sneha_id, 'EDITOR'),
    (v_ai_board_id, v_ananya_id, 'EDITOR')
    ON CONFLICT (board_id, user_id) DO NOTHING;

    -- 5. Fetch Column IDs
    SELECT id INTO v_pay_todo_col FROM board_columns WHERE board_id = v_pay_board_id AND column_type = 'TODO' LIMIT 1;
    SELECT id INTO v_pay_prog_col FROM board_columns WHERE board_id = v_pay_board_id AND column_type = 'IN_PROGRESS' LIMIT 1;
    SELECT id INTO v_pay_done_col FROM board_columns WHERE board_id = v_pay_board_id AND column_type = 'DONE' LIMIT 1;

    SELECT id INTO v_fin_todo_col FROM board_columns WHERE board_id = v_fin_board_id AND column_type = 'TODO' LIMIT 1;
    SELECT id INTO v_fin_prog_col FROM board_columns WHERE board_id = v_fin_board_id AND column_type = 'IN_PROGRESS' LIMIT 1;
    SELECT id INTO v_fin_done_col FROM board_columns WHERE board_id = v_fin_board_id AND column_type = 'DONE' LIMIT 1;

    SELECT id INTO v_ai_todo_col FROM board_columns WHERE board_id = v_ai_board_id AND column_type = 'TODO' LIMIT 1;
    SELECT id INTO v_ai_prog_col FROM board_columns WHERE board_id = v_ai_board_id AND column_type = 'IN_PROGRESS' LIMIT 1;
    SELECT id INTO v_ai_done_col FROM board_columns WHERE board_id = v_ai_board_id AND column_type = 'DONE' LIMIT 1;

    -- 6. Insert Real Tasks
    -- Set session user so triggers log proper actor attribution
    PERFORM set_config('app.current_user_id', v_admin_id::TEXT, true);

    -- PAY Board Tasks
    INSERT INTO tasks (board_id, column_id, title, description, priority, assigned_to, created_by, due_date, created_at)
    VALUES (
        v_pay_board_id, v_pay_prog_col,
        'Integrate Razorpay Webhook Callbacks for Auto-Reconciliation',
        'Handle webhook signatures (X-Razorpay-Signature) and update payment ledger asynchronously when UPI transaction events complete.',
        'High', v_rohan_id, v_admin_id, CURRENT_TIMESTAMP + INTERVAL '3 days', v_30d_ago
    ) RETURNING id INTO v_task_pay1;

    INSERT INTO tasks (board_id, column_id, title, description, priority, assigned_to, created_by, due_date, created_at)
    VALUES (
        v_pay_board_id, v_pay_todo_col,
        'Implement Failover Gateway for Failed UPI Intent Transactions',
        'If PhonePe or Paytm intent fails twice within 10s, auto-switch fallback route to Razorpay Standard Checkout.',
        'High', v_ananya_id, v_priya_id, CURRENT_TIMESTAMP + INTERVAL '5 days', v_15d_ago
    ) RETURNING id INTO v_task_pay2;

    INSERT INTO tasks (board_id, column_id, title, description, priority, assigned_to, created_by, due_date, created_at)
    VALUES (
        v_pay_board_id, v_pay_done_col,
        'Fix Refund Status Polling Job Latency in Production',
        'Replaced polling cron job with webhook events. Refund response time dropped from 45 mins to under 2 seconds.',
        'Medium', v_rohan_id, v_admin_id, v_15d_ago, CURRENT_TIMESTAMP - INTERVAL '20 days'
    ) RETURNING id INTO v_task_pay3;

    -- FIN Board Tasks
    INSERT INTO tasks (board_id, column_id, title, description, priority, assigned_to, created_by, due_date, created_at)
    VALUES (
        v_fin_board_id, v_fin_prog_col,
        'Migrate Monolith Auth Service to OAuth2 JWT & Redis Caching',
        'Decouple user session store from PostgreSQL into Redis cluster with automatic JWT token revocation lists.',
        'High', v_rohan_id, v_priya_id, CURRENT_TIMESTAMP + INTERVAL '4 days', v_15d_ago
    ) RETURNING id INTO v_task_fin1;

    INSERT INTO tasks (board_id, column_id, title, description, priority, assigned_to, created_by, due_date, created_at)
    VALUES (
        v_fin_board_id, v_fin_done_col,
        'Optimize PostgreSQL Slow Queries for Transaction History API',
        'Added composite index on (organization_id, created_at) and converted raw queries into canonical view v_transactions_canonical.',
        'High', v_amit_id, v_priya_id, v_15d_ago, CURRENT_TIMESTAMP - INTERVAL '10 days'
    ) RETURNING id INTO v_task_fin2;

    INSERT INTO tasks (board_id, column_id, title, description, priority, assigned_to, created_by, due_date, created_at)
    VALUES (
        v_fin_board_id, v_fin_prog_col,
        'Redesign Merchant Onboarding Dashboard with Dark Mode',
        'Implement responsive glassmorphism theme and multi-step KYC verification wizard using modern design tokens.',
        'Medium', v_sneha_id, v_admin_id, CURRENT_TIMESTAMP + INTERVAL '6 days', v_15d_ago
    ) RETURNING id INTO v_task_fin3;

    -- AI Board Tasks
    INSERT INTO tasks (board_id, column_id, title, description, priority, assigned_to, created_by, due_date, created_at)
    VALUES (
        v_ai_board_id, v_ai_prog_col,
        'Deploy Pinecone Vector DB for Semantic Knowledge Search',
        'Store embedded documentation vectors using OpenAI text-embedding-3-small for real-time customer query resolution.',
        'High', v_ananya_id, v_admin_id, CURRENT_TIMESTAMP + INTERVAL '2 days', v_15d_ago
    ) RETURNING id INTO v_task_ai1;

    -- 7. Add Authentic Comments
    INSERT INTO task_comments (task_id, user_id, content, created_at) VALUES
    (v_task_pay1, v_priya_id, '@Rohan Gupta Make sure we validate HTTP 504 gateway timeouts gracefully so double debit does not happen on UPI.', CURRENT_TIMESTAMP - INTERVAL '5 days'),
    (v_task_pay1, v_rohan_id, 'Added idempotent request IDs on Redis to deduplicate webhook retries from Razorpay.', CURRENT_TIMESTAMP - INTERVAL '4 days'),
    (v_task_pay1, v_admin_id, 'Great progress! Let us deploy this to staging for final QA before Friday release.', CURRENT_TIMESTAMP - INTERVAL '2 days'),

    (v_task_fin1, v_rohan_id, 'Benchmarked Redis cache performance: auth token verification latency dropped from 120ms to 4ms.', CURRENT_TIMESTAMP - INTERVAL '3 days'),
    (v_task_fin1, v_priya_id, 'Awesome work @Rohan Gupta. Please review the security audit checklist before merging PR #142.', CURRENT_TIMESTAMP - INTERVAL '1 day'),

    (v_task_fin3, v_sneha_id, 'Updated Figma UI components with Indian Rupee formatting and primary brand colors.', CURRENT_TIMESTAMP - INTERVAL '2 hours');

    -- 8. Add Recent Activity Events & Target Notifications for Admin (Rajesh Sharma)
    PERFORM set_config('app.current_user_id', v_priya_id::TEXT, true);

    -- Create activities
    INSERT INTO activities (organization_id, entity_type, entity_id, activity_type, user_id, old_value, new_value, created_at)
    VALUES (
        v_org_id, 'TASK', v_task_pay1, 'ASSIGNEE_CHANGED', v_priya_id,
        jsonb_build_object('assigned_to', NULL, 'assignee_name', NULL),
        jsonb_build_object('assigned_to', v_admin_id, 'assignee_name', 'Rajesh Sharma'),
        CURRENT_TIMESTAMP - INTERVAL '3 hours'
    );

    INSERT INTO activities (organization_id, entity_type, entity_id, activity_type, user_id, old_value, new_value, created_at)
    VALUES (
        v_org_id, 'TASK', v_task_fin3, 'STATUS_CHANGED', v_sneha_id,
        jsonb_build_object('column_id', v_fin_todo_col, 'column_name', 'To Do'),
        jsonb_build_object('column_id', v_fin_prog_col, 'column_name', 'In Progress'),
        CURRENT_TIMESTAMP - INTERVAL '1 hour'
    );

    -- Generate unread notifications for admin@techinnovators.com
    INSERT INTO notifications (user_id, activity_id, is_read, created_at)
    SELECT v_admin_id, a.id, false, a.created_at
    FROM activities a
    WHERE a.organization_id = v_org_id;

END $$;
