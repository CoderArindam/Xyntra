-- 020_update_user_profile.sql
-- Function for updating user profile without raw SQL in the application layer

CREATE OR REPLACE FUNCTION fn_update_user_profile(
    p_user_id INTEGER,
    p_first_name VARCHAR DEFAULT NULL,
    p_last_name VARCHAR DEFAULT NULL,
    p_avatar_url VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    id INTEGER,
    email VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    avatar_url VARCHAR,
    role VARCHAR,
    organization_id INTEGER,
    is_email_verified BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    UPDATE users
    SET
        first_name = COALESCE(p_first_name, users.first_name),
        last_name = COALESCE(p_last_name, users.last_name),
        avatar_url = COALESCE(p_avatar_url, users.avatar_url)
    WHERE users.id = p_user_id;

    RETURN QUERY
    SELECT 
        u.id, 
        u.email, 
        u.first_name, 
        u.last_name, 
        u.avatar_url, 
        u.role::VARCHAR, 
        u.organization_id, 
        u.is_email_verified, 
        u.created_at
    FROM users u
    WHERE u.id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
