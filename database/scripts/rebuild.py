import asyncio
import asyncpg
import os
import sys
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env")
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Password%40123@localhost:5432/kanban_test_db")
MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "migrations")

async def rebuild():
    conn = await asyncpg.connect(DATABASE_URL)
    
    reset_db = "--reset" in sys.argv
    if reset_db:
        print("Reset flag detected. Dropping public schema...")

        await conn.execute("CREATE SCHEMA public;")
    else:
        print("Running migrations incrementally without dropping data...")
    
    migration_files = sorted([f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")])
    for filename in migration_files:
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
