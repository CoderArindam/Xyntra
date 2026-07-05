import asyncio
import asyncpg
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def run_migration():
    from app.config.config import settings
    conn = await asyncpg.connect(settings.DATABASE_URL)
    
    filename = sys.argv[1] if len(sys.argv) > 1 else '..\\database\\migrations\\019_project_settings.sql'
    with open(filename, 'r') as f:
        sql = f.read()
    
    try:
        await conn.execute(sql)
        print("Migration executed successfully.")
    except Exception as e:
        print(f"Error executing migration: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())
