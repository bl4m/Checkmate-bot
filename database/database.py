from logging import getLogger
from os import getenv

import asyncpg
from dotenv import load_dotenv

load_dotenv()

logger = getLogger(__name__)

LOCALHOST_POSTGRES = "postgresql://postgres:postgres@localhost:5432/postgres"
POSTGRES_URI = getenv("POSTGRES_URI", LOCALHOST_POSTGRES)
POSTGRES_SSL = getenv("POSTGRES_SSL", "disable" if "localhost" in POSTGRES_URI or "127.0.0.1" in POSTGRES_URI else "require")


class PostgresManager:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    @classmethod
    async def create(cls):
        if POSTGRES_URI == LOCALHOST_POSTGRES:
            logger.warning("Using fallback localhost Postgres URI. Set POSTGRES_URI in .env for production.")

        try:
            ssl_setting = None if POSTGRES_SSL.lower() in {"0", "false", "disable", "off", "none"} else "require"
            pool = await asyncpg.create_pool(
                POSTGRES_URI,
                min_size=1,
                max_size=10,
                ssl=ssl_setting,
            )

            async with pool.acquire() as conn:
                await conn.execute("SELECT 1;")

            logger.info("Successfully connected to Postgres.")
            return cls(pool)

        except Exception as e:
            logger.error(f"Postgres connection failed! {e}")
            raise e

    async def execute(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch_all(self, query: str, *args):
        """Helper to fetch multiple records."""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetch_row(self, query: str, *args):
        """Helper to fetch a single record."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
