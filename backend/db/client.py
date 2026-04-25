"""
Database client — SQLite via aiosqlite.

Zero-configuration: the database file is created automatically at
backend/lumos.db (or wherever DB_PATH env var points).

Drop-in replacement for the original asyncpg client; all function
signatures are identical so main.py is unchanged.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from backend.db.models import SCHEMA_SQL

# ── Config ───────────────────────────────────────────────────────────────────

def _db_path() -> str:
    path = os.getenv("DB_PATH") or str(
        Path(__file__).resolve().parent.parent / "lumos.db"
    )
    return path


# ── Lifecycle ────────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create tables if they don't exist."""
    async with aiosqlite.connect(_db_path()) as db:
        await db.executescript(SCHEMA_SQL)
        await db.commit()


async def close_db() -> None:
    """No persistent pool to close with aiosqlite."""
    pass


# ── Sessions ─────────────────────────────────────────────────────────────────

async def create_session(
    session_id: str, source_doc_name: str, source_doc_text: str
) -> None:
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(
            """
            INSERT INTO sessions
              (id, source_doc_name, source_doc_text, status, iteration_count)
            VALUES (?, ?, ?, 'running', 0)
            """,
            (session_id, source_doc_name, source_doc_text),
        )
        await db.commit()


async def mark_session_complete(
    session_id: str, final_state: dict[str, Any]
) -> None:
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(
            """
            UPDATE sessions
            SET status = 'complete',
                iteration_count = ?,
                result_json = ?,
                error_message = NULL
            WHERE id = ?
            """,
            (
                int(final_state.get("iteration_count", 0)),
                json.dumps(final_state),
                session_id,
            ),
        )
        await db.commit()


async def mark_session_failed(session_id: str, error_message: str) -> None:
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(
            """
            UPDATE sessions
            SET status = 'failed',
                error_message = ?
            WHERE id = ?
            """,
            (error_message[:1000], session_id),
        )
        await db.commit()


async def get_session(session_id: str) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, status, iteration_count, result_json, error_message
            FROM sessions
            WHERE id = ?
            """,
            (session_id,),
        )
        row = await cursor.fetchone()
    if row is None:
        return None
    d = dict(row)
    if d.get("result_json") and isinstance(d["result_json"], str):
        try:
            d["result_json"] = json.loads(d["result_json"])
        except json.JSONDecodeError:
            pass
    return d


# ── Users ────────────────────────────────────────────────────────────────────

async def create_user(
    name: str, email: str, password_hash: str
) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        try:
            cursor = await db.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (name.strip(), email.strip().lower(), password_hash),
            )
            await db.commit()
            user_id = cursor.lastrowid
        except aiosqlite.IntegrityError:
            return None  # email already exists

        cursor = await db.execute(
            "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
        )
        row = await cursor.fetchone()
    if row is None:
        return None
    d = dict(row)
    d["id"] = str(d["id"])
    return d


async def get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (email.strip().lower(),),
        )
        row = await cursor.fetchone()
    if row is None:
        return None
    d = dict(row)
    d["id"] = str(d["id"])
    return d


async def get_user_by_id(user_id: str) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
        )
        row = await cursor.fetchone()
    if row is None:
        return None
    d = dict(row)
    d["id"] = str(d["id"])
    return d
