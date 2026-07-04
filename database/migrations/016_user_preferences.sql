-- 016_user_preferences.sql
-- User Preferences Foundation

-- 1. Create Enums
DO $$ BEGIN
    CREATE TYPE theme_enum AS ENUM ('light', 'dark', 'system');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Create Table
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL UNIQUE,
    theme theme_enum DEFAULT 'system' NOT NULL,
    accent_color VARCHAR(50) DEFAULT 'blue' NOT NULL,
    density VARCHAR(50) DEFAULT 'comfortable' NOT NULL,
    animations_enabled BOOLEAN DEFAULT true NOT NULL,
    language VARCHAR(10) DEFAULT 'en' NOT NULL,
    timezone VARCHAR(100) DEFAULT 'UTC' NOT NULL,
    date_format VARCHAR(50) DEFAULT 'MM/DD/YYYY' NOT NULL,
    time_format VARCHAR(20) DEFAULT '12h' NOT NULL,
    week_start INTEGER DEFAULT 0 NOT NULL, -- 0 = Sunday, 1 = Monday
    default_home_page VARCHAR(100) DEFAULT 'dashboard' NOT NULL,
    default_board_view VARCHAR(50) DEFAULT 'kanban' NOT NULL,
    sidebar_collapsed BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Triggers for updated_at
DROP TRIGGER IF EXISTS trg_user_preferences_updated_at ON user_preferences;
CREATE TRIGGER trg_user_preferences_updated_at
BEFORE UPDATE ON user_preferences
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 4. Trigger to auto-create preferences for new users
CREATE OR REPLACE FUNCTION auto_create_user_preferences()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_preferences (user_id) VALUES (NEW.id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_auto_create_user_preferences ON users;
CREATE TRIGGER trg_auto_create_user_preferences
AFTER INSERT ON users
FOR EACH ROW EXECUTE FUNCTION auto_create_user_preferences();

-- 5. Canonical View
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
    p.created_at,
    p.updated_at
FROM user_preferences p;

-- 6. Functions for getting and updating preferences
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
    p_sidebar_collapsed BOOLEAN DEFAULT NULL
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
        sidebar_collapsed = COALESCE(p_sidebar_collapsed, user_preferences.sidebar_collapsed)
    WHERE user_preferences.user_id = p_user_id;

    RETURN QUERY
    SELECT *
    FROM v_user_preferences_canonical
    WHERE v_user_preferences_canonical.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 7. Seed Data (backfill existing users)
INSERT INTO user_preferences (user_id)
SELECT id FROM users
ON CONFLICT (user_id) DO NOTHING;
