# Database Migration Execution Order

To initialize the kanban database properly, the SQL files must be executed in a strict order to respect foreign key constraints and dependencies. 

Execute the files in the following order:

## 1. Migrations (Tables)
1. `001_create_users_table.sql`
2. `002_create_boards_table.sql`
3. `003_create_board_columns_table.sql`
4. `004_create_tasks_table.sql`

## 2. Functions (PL/pgSQL Business Logic)
After the tables exist, apply the stored functions:
1. `users.sql`
2. `boards.sql`
3. `tasks.sql`

*Note: You can execute the unified setup script in `database/scripts/setup_database.sql` via `psql` to automatically run these in the correct sequence.*
