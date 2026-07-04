-- 015_account_security.sql
-- Refinements for Phase 4.2: Account Security & Session Management

-- 1. Add email verification flag to users
ALTER TABLE users
ADD COLUMN IF NOT EXISTS is_email_verified BOOLEAN DEFAULT true;

-- 2. Normalize user_sessions
ALTER TABLE user_sessions
DROP COLUMN IF EXISTS device_info;

ALTER TABLE user_sessions
ADD COLUMN IF NOT EXISTS browser VARCHAR(100),
ADD COLUMN IF NOT EXISTS platform VARCHAR(100),
ADD COLUMN IF NOT EXISTS device_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP WITH TIME ZONE;

-- 3. Initialize last_active_at for existing sessions
UPDATE user_sessions SET last_active_at = created_at WHERE last_active_at IS NULL;
