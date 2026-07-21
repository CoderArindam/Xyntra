import asyncio
import asyncpg
import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env")
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Password%40123@localhost:5432/kanban_test_db")
MIGRATION_FILE = os.path.join(os.path.dirname(__file__), "..", "migrations", "036_dashboard_views.sql")

async def apply():
    conn = await asyncpg.connect(DATABASE_URL)
    with open(MIGRATION_FILE, "r", encoding="utf-8") as f:
        sql = f.read()
    print("Applying 036_dashboard_views.sql...")
    await conn.execute(sql)
    print("Applied 036_dashboard_views.sql successfully!")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(apply())
