"""
Database connection and query utilities for PostgreSQL.
"""
import asyncpg
import os
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cdn_user:cdn_pass@localhost:5432/cdn_dev")

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def init_db_pool():
    """Initialize the database connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return _pool


async def close_db_pool():
    """Close the database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def get_pool() -> asyncpg.Pool:
    """Get the database connection pool."""
    if _pool is None:
        await init_db_pool()
    return _pool


@asynccontextmanager
async def get_db_connection():
    """
    Context manager for database connections.

    Usage:
        async with get_db_connection() as conn:
            result = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    """
    pool = await get_pool()
    async with pool.acquire() as connection:
        yield connection


async def execute_query(query: str, *args) -> str:
    """Execute a query (INSERT, UPDATE, DELETE) and return status."""
    async with get_db_connection() as conn:
        result = await conn.execute(query, *args)
        return result


async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    """Fetch a single row."""
    async with get_db_connection() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_all(query: str, *args) -> List[Dict[str, Any]]:
    """Fetch all rows."""
    async with get_db_connection() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def fetch_val(query: str, *args) -> Any:
    """Fetch a single value."""
    async with get_db_connection() as conn:
        return await conn.fetchval(query, *args)
