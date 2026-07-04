-- 001_extensions.sql
-- Core extensions required by the application

-- For UUID generation (e.g. refresh tokens or external IDs)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- For full-text search capability
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
