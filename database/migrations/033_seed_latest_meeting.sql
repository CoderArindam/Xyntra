-- 033_seed_latest_meeting.sql
-- Simulate a freshly completed Google Meet call for TechInnovators India with 4 AI-extracted task proposals ready for review

DO $$
DECLARE
    v_org_id INTEGER;
    v_admin_id INTEGER;
    v_priya_id INTEGER;
    v_rohan_id INTEGER;
    v_sneha_id INTEGER;
    v_amit_id INTEGER;
    v_ananya_id INTEGER;

    v_pay_board_id INTEGER;
    v_fin_board_id INTEGER;
    v_ai_board_id INTEGER;

    v_session_uuid UUID := uuid_generate_v4();
    v_activity_id INTEGER;
BEGIN
    -- 1. Fetch TechInnovators organization and user IDs
    SELECT id INTO v_org_id FROM organizations WHERE name = 'TechInnovators India' LIMIT 1;
    IF v_org_id IS NULL THEN
        SELECT organization_id INTO v_org_id FROM users WHERE email = 'admin@techinnovators.com' LIMIT 1;
    END IF;

    SELECT id INTO v_admin_id FROM users WHERE email = 'admin@techinnovators.com' LIMIT 1;
    SELECT id INTO v_priya_id FROM users WHERE email = 'priya.patel@techinnovators.com' LIMIT 1;
    SELECT id INTO v_rohan_id FROM users WHERE email = 'rohan.gupta@techinnovators.com' LIMIT 1;
    SELECT id INTO v_sneha_id FROM users WHERE email = 'sneha.reddy@techinnovators.com' LIMIT 1;
    SELECT id INTO v_amit_id FROM users WHERE email = 'amit.kumar@techinnovators.com' LIMIT 1;
    SELECT id INTO v_ananya_id FROM users WHERE email = 'ananya.rao@techinnovators.com' LIMIT 1;

    -- Fetch Board IDs
    SELECT id INTO v_pay_board_id FROM boards WHERE organization_id = v_org_id AND project_key = 'PAY' LIMIT 1;
    SELECT id INTO v_fin_board_id FROM boards WHERE organization_id = v_org_id AND project_key = 'FIN' LIMIT 1;
    SELECT id INTO v_ai_board_id FROM boards WHERE organization_id = v_org_id AND project_key = 'AI' LIMIT 1;

    -- 2. Insert Completed Meeting Session
    INSERT INTO meeting_sessions (
        id, session_id, meeting_url, status, started_at, created_at, org_id, initiated_by_user_id, source
    ) VALUES (
        v_session_uuid,
        'meet-techinnovators-q3-sync',
        'https://meet.google.com/tech-innovators-sprint-sync',
        'completed',
        CURRENT_TIMESTAMP - INTERVAL '45 minutes',
        CURRENT_TIMESTAMP - INTERVAL '2 minutes',
        v_org_id,
        v_admin_id,
        'manual'
    ) ON CONFLICT (id) DO NOTHING;

    -- 3. Insert Task Proposals
    -- Proposal 1: Distributed Lock for UPI Webhooks
    INSERT INTO task_proposals (
        org_id, board_id, meeting_session_id, title, description,
        suggested_assignee_id, confidence_score, source_transcript_quote,
        status, priority, due_date, raw_llm_payload, created_at, board_confidence, board_source
    ) VALUES (
        v_org_id, v_pay_board_id, v_session_uuid,
        'Implement Redis Distributed Lock for Concurrent UPI Webhook Callbacks',
        'Prevent race conditions and double-ledger credits when multiple webhook callbacks hit the payment gateway simultaneously during flash sales.',
        v_rohan_id, 0.95,
        '"@Rohan Gupta, during IPL flash sales we saw duplicate webhook hits causing double ledger entries. We need a Redis distributed lock (Redlock) on transaction_id before processing callbacks." - Priya Patel',
        'pending', 'HIGH', CURRENT_TIMESTAMP + INTERVAL '3 days',
        jsonb_build_object('llm_reasoning', 'High confidence match for Razorpay & UPI V2 Sync board based on Webhook & UPI keywords.'),
        CURRENT_TIMESTAMP - INTERVAL '2 minutes',
        0.96, 'llm_matched'
    );

    -- Proposal 2: Prometheus & Grafana Alerts
    INSERT INTO task_proposals (
        org_id, board_id, meeting_session_id, title, description,
        suggested_assignee_id, confidence_score, source_transcript_quote,
        status, priority, due_date, raw_llm_payload, created_at, board_confidence, board_source
    ) VALUES (
        v_org_id, v_fin_board_id, v_session_uuid,
        'Setup Prometheus & Grafana Dashboards for API Latency Alerts',
        'Configure P99 latency thresholds and 5xx error rate alert rules with instant Slack webhook notifications for the Core Migration microservices.',
        v_amit_id, 0.92,
        '"@Amit Kumar, please spin up Grafana alert thresholds for P99 latency exceeding 200ms on the OAuth2 auth service so DevOps gets paged immediately." - Rajesh Sharma',
        'pending', 'HIGH', CURRENT_TIMESTAMP + INTERVAL '4 days',
        jsonb_build_object('llm_reasoning', 'Matched Fintech Platform Core Migration board based on API & microservice monitoring context.'),
        CURRENT_TIMESTAMP - INTERVAL '2 minutes',
        0.91, 'llm_matched'
    );

    -- Proposal 3: Mobile KYC UI
    INSERT INTO task_proposals (
        org_id, board_id, meeting_session_id, title, description,
        suggested_assignee_id, confidence_score, source_transcript_quote,
        status, priority, due_date, raw_llm_payload, created_at, board_confidence, board_source
    ) VALUES (
        v_org_id, v_fin_board_id, v_session_uuid,
        'Design Mobile KYC Selfie & Document Auto-Capture Flow',
        'Create interactive Figma prototypes and UI components for real-time PAN & Aadhaar OCR document scanning during merchant onboarding.',
        v_sneha_id, 0.89,
        '"@Sneha Reddy, merchants are dropping off during manual PAN upload. Can you design an auto-capture OCR camera interface with real-time feedback?" - Priya Patel',
        'pending', 'MEDIUM', CURRENT_TIMESTAMP + INTERVAL '5 days',
        jsonb_build_object('llm_reasoning', 'Matched Fintech Platform Core Migration board based on merchant onboarding UI keywords.'),
        CURRENT_TIMESTAMP - INTERVAL '2 minutes',
        0.88, 'llm_matched'
    );

    -- Proposal 4: LLM Benchmark
    INSERT INTO task_proposals (
        org_id, board_id, meeting_session_id, title, description,
        suggested_assignee_id, confidence_score, source_transcript_quote,
        status, priority, due_date, raw_llm_payload, created_at, board_confidence, board_source
    ) VALUES (
        v_org_id, v_ai_board_id, v_session_uuid,
        'Evaluate OpenAI GPT-4o vs Claude 3.5 Sonnet for AI Co-Pilot',
        'Benchmark customer support query classification accuracy, response latency, and cost per 1k tokens on our internal dataset.',
        v_ananya_id, 0.87,
        '"@Ananya Rao, compare GPT-4o and Sonnet 3.5 on our support transcript dataset and present the latency vs cost trade-off matrix." - Rajesh Sharma',
        'pending', 'MEDIUM', CURRENT_TIMESTAMP + INTERVAL '2 days',
        jsonb_build_object('llm_reasoning', 'Matched AI Co-Pilot & Customer Analytics board based on LLM & AI evaluation keywords.'),
        CURRENT_TIMESTAMP - INTERVAL '2 minutes',
        0.95, 'llm_matched'
    );

    -- 4. Create Activity & Notification for Proposals Ready
    INSERT INTO activities (
        organization_id, entity_type, entity_id, activity_type, user_id, old_value, new_value, metadata, created_at
    ) VALUES (
        v_org_id, 'ORGANIZATION', v_org_id, 'UPDATED', v_admin_id,
        NULL,
        jsonb_build_object('session_id', 'meet-techinnovators-q3-sync', 'count', 4, 'meeting_url', 'https://meet.google.com/tech-innovators-sprint-sync'),
        jsonb_build_object('meeting_title', 'TechInnovators Q3 Sprint & Architecture Alignment Call'),
        CURRENT_TIMESTAMP - INTERVAL '1 minute'
    ) RETURNING id INTO v_activity_id;

    -- Add Notification for Admin (Rajesh Sharma) and Manager (Priya Patel)
    INSERT INTO notifications (user_id, activity_id, is_read, created_at)
    VALUES 
    (v_admin_id, v_activity_id, false, CURRENT_TIMESTAMP - INTERVAL '1 minute'),
    (v_priya_id, v_activity_id, false, CURRENT_TIMESTAMP - INTERVAL '1 minute');

END $$;
