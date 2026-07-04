-- 002_enums.sql
-- Strong ENUM types for application state

-- Role ENUM for users in an organization
DO $$ BEGIN
    CREATE TYPE role_enum AS ENUM ('MEMBER', 'MANAGER', 'SUPER_ADMIN');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Permission ENUM for board access
DO $$ BEGIN
    CREATE TYPE permission_enum AS ENUM ('VIEWER', 'EDITOR', 'OWNER');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Column Type ENUM for task states
DO $$ BEGIN
    CREATE TYPE column_type_enum AS ENUM ('TODO', 'IN_PROGRESS', 'DONE');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Entity Type ENUM for polymorphic references (activities, comments, etc.)
DO $$ BEGIN
    CREATE TYPE entity_type_enum AS ENUM ('TASK', 'BOARD', 'COMMENT', 'USER', 'ORGANIZATION');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Activity Type ENUM
DO $$ BEGIN
    CREATE TYPE activity_type_enum AS ENUM (
        'CREATED',
        'UPDATED',
        'DELETED',
        'STATUS_CHANGED',
        'ASSIGNEE_CHANGED',
        'COMMENT_ADDED',
        'ATTACHMENT_ADDED',
        'DUE_DATE_CHANGED'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;
