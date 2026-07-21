-- 034_security_event_functions.sql
-- UDFs and canonical view for Phase C6: Recent Login Activity security events

-- 1. Helper function to log security/audit events
CREATE OR REPLACE FUNCTION fn_log_security_event(
    p_org_id INTEGER,
    p_user_id INTEGER,
    p_action VARCHAR,
    p_entity_type entity_type_enum,
    p_entity_id INTEGER,
    p_ip_address VARCHAR,
    p_details JSONB DEFAULT '{}'::jsonb
) RETURNS INTEGER AS $$
DECLARE
    v_log_id INTEGER;
BEGIN
    INSERT INTO audit_logs (organization_id, user_id, action, entity_type, entity_id, ip_address, details)
    VALUES (p_org_id, p_user_id, p_action, p_entity_type, p_entity_id, p_ip_address, p_details)
    RETURNING id INTO v_log_id;

    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- 2. Function to check if a login is from an unrecognized / new device
CREATE OR REPLACE FUNCTION fn_check_is_new_device(
    p_user_id INTEGER,
    p_browser VARCHAR,
    p_platform VARCHAR
) RETURNS BOOLEAN AS $$
DECLARE
    v_session_exists BOOLEAN;
    v_audit_exists BOOLEAN;
BEGIN
    -- Check user_sessions table
    SELECT EXISTS (
        SELECT 1 
        FROM user_sessions 
        WHERE user_id = p_user_id 
          AND browser = p_browser 
          AND platform = p_platform
    ) INTO v_session_exists;

    IF v_session_exists THEN
        RETURN FALSE;
    END IF;

    -- Check audit_logs table for prior successful logins with matching device info
    SELECT EXISTS (
        SELECT 1 
        FROM audit_logs 
        WHERE user_id = p_user_id 
          AND action IN ('LOGIN', 'NEW_DEVICE_LOGIN') 
          AND (details->>'browser') = p_browser 
          AND (details->>'platform') = p_platform
    ) INTO v_audit_exists;

    RETURN NOT v_audit_exists;
END;
$$ LANGUAGE plpgsql;

-- 3. Canonical view for security events
CREATE OR REPLACE VIEW v_security_events_canonical AS
SELECT 
    id,
    organization_id,
    user_id,
    action,
    entity_type,
    entity_id,
    ip_address,
    details,
    created_at
FROM audit_logs;

-- 4. Function to fetch user security events
CREATE OR REPLACE FUNCTION fn_get_user_security_events(
    p_user_id INTEGER,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    id INTEGER,
    organization_id INTEGER,
    user_id INTEGER,
    action VARCHAR,
    entity_type entity_type_enum,
    entity_id INTEGER,
    ip_address VARCHAR,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.id,
        v.organization_id,
        v.user_id,
        v.action,
        v.entity_type,
        v.entity_id,
        v.ip_address,
        v.details,
        v.created_at
    FROM v_security_events_canonical v
    WHERE v.user_id = p_user_id
    ORDER BY v.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
