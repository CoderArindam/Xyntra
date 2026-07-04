import asyncpg
from typing import AsyncGenerator
from app.config.config import settings

import json

async def init_connection(conn):
    await conn.set_type_codec('jsonb', encoder=json.dumps, decoder=json.loads, schema='pg_catalog')
    await conn.set_type_codec('json', encoder=json.dumps, decoder=json.loads, schema='pg_catalog')

class Database:
    def __init__(self):
        self.pool: asyncpg.Pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=1,
            max_size=10,
            init=init_connection
        )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

db = Database()

async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    if not db.pool:
        raise Exception("Database pool is not initialized")
    async with db.pool.acquire() as connection:
        yield connection
