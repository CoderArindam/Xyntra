-- 035_auth_session_functions.sql
-- Canonical views and PostgreSQL UDFs for Auth and Session Management

-- 1. Canonical View for Users
DROP VIEW IF EXISTS v_users_canonical CASCADE;
CREATE OR REPLACE VIEW v_users_canonical AS
SELECT 
    id,
    organization_id,
    email,
    password_hash,
    first_name,
    last_name,
    avatar_url,
    role,
    is_email_verified,
    created_at,
    deleted_at
FROM users
WHERE deleted_at IS NULL;

-- 2. Canonical View for User Sessions
DROP VIEW IF EXISTS v_user_sessions_canonical CASCADE;
CREATE OR REPLACE VIEW v_user_sessions_canonical AS
SELECT 
    id,
    user_id,
    refresh_token_hash,
    browser,
    platform,
    device_name,
    ip_address,
    expires_at,
    revoked_at,
    created_at,
    last_active_at
FROM user_sessions;

-- 3. Function to create a user session
CREATE OR REPLACE FUNCTION fn_create_user_session(
    p_user_id INTEGER,
    p_refresh_token_hash VARCHAR,
    p_browser VARCHAR,
    p_platform VARCHAR,
    p_device_name VARCHAR,
    p_ip_address VARCHAR,
    p_expires_at TIMESTAMP WITH TIME ZONE
) RETURNS INTEGER AS $$
DECLARE
    v_session_id INTEGER;
BEGIN
    INSERT INTO user_sessions (
        user_id, 
        refresh_token_hash, 
        browser, 
        platform, 
        device_name, 
        ip_address, 
        expires_at, 
        last_active_at
    )
    VALUES (
        p_user_id, 
        p_refresh_token_hash, 
        p_browser, 
        p_platform, 
        p_device_name, 
        p_ip_address, 
        p_expires_at, 
        CURRENT_TIMESTAMP
    )
    RETURNING id INTO v_session_id;

    RETURN v_session_id;
END;
$$ LANGUAGE plpgsql;

-- 4. Function to refresh a user session in-place
CREATE OR REPLACE FUNCTION fn_refresh_user_session(
    p_token_hash VARCHAR,
    p_new_token_hash VARCHAR,
    p_expires_at TIMESTAMP WITH TIME ZONE,
    p_browser VARCHAR DEFAULT NULL,
    p_platform VARCHAR DEFAULT NULL,
    p_ip_address VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    session_id INTEGER,
    user_id INTEGER
) AS $$
DECLARE
    v_session_id INTEGER;
    v_user_id INTEGER;
    v_revoked_at TIMESTAMP WITH TIME ZONE;
    v_expires_at TIMESTAMP WITH TIME ZONE;
BEGIN
    SELECT s.id, s.user_id, s.revoked_at, s.expires_at 
    INTO v_session_id, v_user_id, v_revoked_at, v_expires_at
    FROM user_sessions s
    WHERE s.refresh_token_hash = p_token_hash;

    IF v_session_id IS NULL THEN
        RETURN;
    END IF;

    IF v_revoked_at IS NOT NULL OR v_expires_at < CURRENT_TIMESTAMP THEN
        RETURN;
    END IF;

    UPDATE user_sessions
    SET refresh_token_hash = p_new_token_hash,
        expires_at = p_expires_at,
        last_active_at = CURRENT_TIMESTAMP,
        browser = COALESCE(p_browser, browser),
        platform = COALESCE(p_platform, platform),
        ip_address = COALESCE(p_ip_address, ip_address)
    WHERE id = v_session_id;

    RETURN QUERY SELECT v_session_id, v_user_id;
END;
$$ LANGUAGE plpgsql;

-- 5. Function to fetch active user sessions
CREATE OR REPLACE FUNCTION fn_get_user_sessions(
    p_user_id INTEGER
)
RETURNS TABLE (
    id INTEGER,
    browser VARCHAR,
    platform VARCHAR,
    device_name VARCHAR,
    ip_address VARCHAR,
    last_active_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE,
    refresh_token_hash VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id,
        s.browser,
        s.platform,
        s.device_name,
        s.ip_address,
        s.last_active_at,
        s.created_at,
        s.refresh_token_hash
    FROM v_user_sessions_canonical s
    WHERE s.user_id = p_user_id 
      AND s.revoked_at IS NULL 
      AND s.expires_at > CURRENT_TIMESTAMP
    ORDER BY s.last_active_at DESC NULLS LAST;
END;
$$ LANGUAGE plpgsql;

-- 6. Function to revoke a session by refresh token hash
CREATE OR REPLACE FUNCTION fn_revoke_session_by_token_hash(
    p_token_hash VARCHAR
) RETURNS VOID AS $$
BEGIN
    UPDATE user_sessions
    SET revoked_at = CURRENT_TIMESTAMP
    WHERE refresh_token_hash = p_token_hash
      AND revoked_at IS NULL;
END;
$$ LANGUAGE plpgsql;

-- 7. Function to revoke other sessions of a user (preserving current session)
CREATE OR REPLACE FUNCTION fn_revoke_other_user_sessions(
    p_user_id INTEGER,
    p_current_session_id INTEGER DEFAULT NULL,
    p_current_token_hash VARCHAR DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_revoked_count INTEGER;
BEGIN
    IF p_current_session_id IS NULL AND p_current_token_hash IS NULL THEN
        RETURN 0;
    END IF;

    WITH updated AS (
        UPDATE user_sessions
        SET revoked_at = CURRENT_TIMESTAMP
        WHERE user_id = p_user_id
          AND revoked_at IS NULL
          AND NOT (
              (p_current_session_id IS NOT NULL AND id = p_current_session_id)
              OR
              (p_current_token_hash IS NOT NULL AND refresh_token_hash = p_current_token_hash)
          )
        RETURNING id
    )
    SELECT COUNT(*)::INTEGER INTO v_revoked_count FROM updated;

    RETURN v_revoked_count;
END;
$$ LANGUAGE plpgsql;

-- 8. Function to check if a session is revoked
CREATE OR REPLACE FUNCTION fn_is_session_revoked(
    p_session_id INTEGER
) RETURNS BOOLEAN AS $$
DECLARE
    v_revoked_at TIMESTAMP WITH TIME ZONE;
    v_found BOOLEAN := FALSE;
BEGIN
    SELECT TRUE, revoked_at INTO v_found, v_revoked_at
    FROM user_sessions
    WHERE id = p_session_id;

    IF NOT v_found OR v_revoked_at IS NOT NULL THEN
        RETURN TRUE;
    END IF;

    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;
