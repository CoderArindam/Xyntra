-- 017_appearance_updates.sql
-- Add sidebar_theme to user_preferences

ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS sidebar_theme VARCHAR(50) DEFAULT 'default' NOT NULL;

-- Update canonical view
DROP VIEW IF EXISTS v_user_preferences_canonical CASCADE;
CREATE OR REPLACE VIEW v_user_preferences_canonical AS
SELECT
    p.id,
    p.user_id,
    p.theme,
    p.accent_color,
    p.density,
    p.animations_enabled,
    p.language,
    p.timezone,
    p.date_format,
    p.time_format,
    p.week_start,
    p.default_home_page,
    p.default_board_view,
    p.sidebar_collapsed,
    p.sidebar_theme,
    p.created_at,
    p.updated_at
FROM user_preferences p;

-- Update functions
DROP FUNCTION IF EXISTS fn_get_user_preferences(integer);
CREATE OR REPLACE FUNCTION fn_get_user_preferences(p_user_id INTEGER)
RETURNS TABLE (
    id INTEGER,
    user_id INTEGER,
    theme theme_enum,
    accent_color VARCHAR(50),
    density VARCHAR(50),
    animations_enabled BOOLEAN,
    language VARCHAR(10),
    timezone VARCHAR(100),
    date_format VARCHAR(50),
    time_format VARCHAR(20),
    week_start INTEGER,
    default_home_page VARCHAR(100),
    default_board_view VARCHAR(50),
    sidebar_collapsed BOOLEAN,
    sidebar_theme VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM v_user_preferences_canonical
    WHERE v_user_preferences_canonical.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP FUNCTION IF EXISTS fn_update_user_preferences(integer, theme_enum, character varying, character varying, boolean, character varying, character varying, character varying, character varying, integer, character varying, character varying, boolean);
CREATE OR REPLACE FUNCTION fn_update_user_preferences(
    p_user_id INTEGER,
    p_theme theme_enum DEFAULT NULL,
    p_accent_color VARCHAR(50) DEFAULT NULL,
    p_density VARCHAR(50) DEFAULT NULL,
    p_animations_enabled BOOLEAN DEFAULT NULL,
    p_language VARCHAR(10) DEFAULT NULL,
    p_timezone VARCHAR(100) DEFAULT NULL,
    p_date_format VARCHAR(50) DEFAULT NULL,
    p_time_format VARCHAR(20) DEFAULT NULL,
    p_week_start INTEGER DEFAULT NULL,
    p_default_home_page VARCHAR(100) DEFAULT NULL,
    p_default_board_view VARCHAR(50) DEFAULT NULL,
    p_sidebar_collapsed BOOLEAN DEFAULT NULL,
    p_sidebar_theme VARCHAR(50) DEFAULT NULL
)
RETURNS TABLE (
    id INTEGER,
    user_id INTEGER,
    theme theme_enum,
    accent_color VARCHAR(50),
    density VARCHAR(50),
    animations_enabled BOOLEAN,
    language VARCHAR(10),
    timezone VARCHAR(100),
    date_format VARCHAR(50),
    time_format VARCHAR(20),
    week_start INTEGER,
    default_home_page VARCHAR(100),
    default_board_view VARCHAR(50),
    sidebar_collapsed BOOLEAN,
    sidebar_theme VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    UPDATE user_preferences
    SET
        theme = COALESCE(p_theme, user_preferences.theme),
        accent_color = COALESCE(p_accent_color, user_preferences.accent_color),
        density = COALESCE(p_density, user_preferences.density),
        animations_enabled = COALESCE(p_animations_enabled, user_preferences.animations_enabled),
        language = COALESCE(p_language, user_preferences.language),
        timezone = COALESCE(p_timezone, user_preferences.timezone),
        date_format = COALESCE(p_date_format, user_preferences.date_format),
        time_format = COALESCE(p_time_format, user_preferences.time_format),
        week_start = COALESCE(p_week_start, user_preferences.week_start),
        default_home_page = COALESCE(p_default_home_page, user_preferences.default_home_page),
        default_board_view = COALESCE(p_default_board_view, user_preferences.default_board_view),
        sidebar_collapsed = COALESCE(p_sidebar_collapsed, user_preferences.sidebar_collapsed),
        sidebar_theme = COALESCE(p_sidebar_theme, user_preferences.sidebar_theme)
    WHERE user_preferences.user_id = p_user_id;

    RETURN QUERY
    SELECT *
    FROM v_user_preferences_canonical
    WHERE v_user_preferences_canonical.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
