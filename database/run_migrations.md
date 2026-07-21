# Database Migration Execution Order

To initialize the KAIO database properly, SQL migration files in `database/migrations/` must be executed in strict numerical sequence to satisfy enum definitions, foreign key constraints, canonical views, and stored procedure dependencies.

## 1. Migrations (001 to 035)

Execute the scripts in the following order:

```powershell
001_extensions.sql
002_enums.sql
003_schema_core.sql
004_indexes.sql
005_functions_authz.sql
006_functions_mutations.sql
007_triggers.sql
008_views.sql
009_seed_data.sql
010_admin_functions.sql
011_invitation_functions.sql
012_authz_refinements.sql
013_fix_task_authz.sql
014_notification_enhancements.sql
015_account_security.sql
016_user_preferences.sql
017_appearance_updates.sql
018_organization_profile.sql
019_project_settings.sql
020_update_user_profile.sql
021_task_proposals_schema.sql
022_task_proposals_view.sql
023_task_proposals_functions.sql
024_task_proposals_hardening.sql
025_task_proposals_nullable_board.sql
026_meeting_sessions_org_scope.sql
027_task_proposals_priority_due_date.sql
028_users_email_unique.sql
029_comment_functions.sql
030_activity_logging_enhancements.sql
031_notification_canonical_enhancements.sql
032_seed_techinnovators.sql
033_seed_latest_meeting.sql
034_security_event_functions.sql
035_auth_session_functions.sql
```

## 2. Automated Migration Script

You can execute the setup scripts in `database/scripts/` via `psql` to automatically run all migrations in sequence:

```bash
psql -U postgres -d kaio_db -f database/scripts/run_all_migrations.sql
```

