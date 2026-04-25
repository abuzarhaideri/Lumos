import json
import os
from typing import Any, Optional

import asyncpg

from backend.db.models import SCHEMA_SQL

_pool: Optional[asyncpg.Pool] = None


def _database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    return database_url


async def init_db() -> None:
    global _pool
    if _pool is not None:
        return
    _pool = await asyncpg.create_pool(_database_url(), min_size=1, max_size=5)
    async with _pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)


async def close_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def create_session(session_id: str, source_doc_name: str, source_doc_text: str) -> None:
    assert _pool is not None, "Database pool not initialized."
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO sessions (id, source_doc_name, source_doc_text, status, iteration_count)
            VALUES ($1::uuid, $2, $3, 'running', 0)
            """,
            session_id,
            source_doc_name,
            source_doc_text,
        )


async def mark_session_complete(session_id: str, final_state: dict[str, Any]) -> None:
    assert _pool is not None, "Database pool not initialized."
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE sessions
            SET status = 'complete',
                iteration_count = $2,
                result_json = $3::jsonb,
                error_message = NULL
            WHERE id = $1::uuid
            """,
            session_id,
            int(final_state.get("iteration_count", 0)),
            json.dumps(final_state),
        )


async def mark_session_failed(session_id: str, error_message: str) -> None:
    assert _pool is not None, "Database pool not initialized."
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE sessions
            SET status = 'failed',
                error_message = $2
            WHERE id = $1::uuid
            """,
            session_id,
            error_message[:1000],
        )


async def get_session(session_id: str) -> Optional[dict[str, Any]]:
    assert _pool is not None, "Database pool not initialized."
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id::text, status, iteration_count, result_json, error_message
            FROM sessions
            WHERE id = $1::uuid
            """,
            session_id,
        )
    return dict(row) if row else None

