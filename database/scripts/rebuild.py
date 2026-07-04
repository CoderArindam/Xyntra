import asyncio
import asyncpg
import os
import sys

DATABASE_URL = "postgresql://postgres:Password%40123@localhost:5432/kanban_db"
MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "migrations")

FILES_TO_RUN = [
    "001_extensions.sql",
    "002_enums.sql",
    "003_schema_core.sql",
    "004_indexes.sql",
    "005_functions_authz.sql",
    "006_functions_mutations.sql",
    "007_triggers.sql",
    "008_views.sql",
    "009_seed_data.sql"
]

async def rebuild():
    conn = await asyncpg.connect(DATABASE_URL)
    
    print("Dropping public schema...")
    await conn.execute("DROP SCHEMA public CASCADE;")
    await conn.execute("CREATE SCHEMA public;")
    
    for filename in FILES_TO_RUN:
        filepath = os.path.join(MIGRATIONS_DIR, filename)
        print(f"Executing {filename}...")
        with open(filepath, "r", encoding="utf-8") as f:
            sql = f.read()
        try:
            await conn.execute(sql)
        except Exception as e:
            print(f"Error in {filename}:\n{e}")
            sys.exit(1)
            
    print("Database rebuild complete!")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(rebuild())
