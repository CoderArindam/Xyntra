-- rebuild_database.sql
-- Master script to drop and rebuild the V2 database

\echo 'WARNING: Dropping public schema...'
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

\echo 'Executing migrations...'
\i ../migrations/001_extensions.sql
\i ../migrations/002_enums.sql
\i ../migrations/003_schema_core.sql
\i ../migrations/004_indexes.sql
\i ../migrations/005_functions_authz.sql
\i ../migrations/006_functions_mutations.sql
\i ../migrations/007_triggers.sql
\i ../migrations/008_views.sql
\i ../migrations/009_seed_data.sql
\i ../migrations/034_security_event_functions.sql
\i ../migrations/035_auth_session_functions.sql

\echo 'Database rebuild complete!'
