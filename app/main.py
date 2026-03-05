"""
main.py — FastAPI application entry point.
- Reads secrets from /run/secrets/app.env (rendered by Vault Agent)
- Inserts a random Base64 string into PostgreSQL every second
- Watches for secret file changes and rotates the DB pool automatically
"""

from __future__ import annotations

import asyncio
import base64
import logging
import secrets
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from fastapi import FastAPI

from db import (
    SECRETS_FILE,
    SECRETS_POLL,
    DB_RETRY_DELAY,
    parse_env_file,
    wait_for_secrets,
    create_pool,
    ensure_schema,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("app")

INSERT_INTERVAL = 1.0   # seconds between inserts

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_pool:        Optional[asyncpg.Pool] = None
_current_env: dict[str, str]         = {}
_env_mtime:   float                  = 0.0


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------

async def inserter_loop() -> None:
    """Insert one random Base64 string per second."""
    log.info("Inserter loop started.")
    while True:
        try:
            value = base64.b64encode(secrets.token_bytes(32)).decode()
            async with _pool.acquire() as conn:
                row = await conn.fetchrow(
                    "INSERT INTO random_strings (value) VALUES ($1) RETURNING id, inserted_at",
                    value,
                )
            log.info("Inserted id=%d  value=%.24s…  at %s", row["id"], value, row["inserted_at"])
        except Exception as exc:
            log.error("Insert error: %s", exc)
            await asyncio.sleep(DB_RETRY_DELAY)
            continue
        await asyncio.sleep(INSERT_INTERVAL)


async def secrets_watchdog() -> None:
    """
    Poll the secrets file for changes.
    When Vault Agent re-renders (e.g. after secret rotation),
    the pool is rebuilt with the new DATABASE_URL — zero downtime.
    """
    global _pool, _current_env, _env_mtime

    while True:
        await asyncio.sleep(SECRETS_POLL)
        try:
            mtime = SECRETS_FILE.stat().st_mtime
        except FileNotFoundError:
            continue

        if mtime <= _env_mtime:
            continue

        new_env = parse_env_file(SECRETS_FILE)
        new_url = new_env.get("DATABASE_URL")
        if not new_url or new_url == _current_env.get("DATABASE_URL"):
            _env_mtime = mtime
            continue

        log.info("Secrets changed — rotating DB pool…")
        old_pool   = _pool
        _pool      = await create_pool(new_url)
        await ensure_schema(_pool)
        _current_env = new_env
        _env_mtime   = mtime

        if old_pool:
            await old_pool.close()
        log.info("DB pool rotated successfully.")


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool, _current_env, _env_mtime

    _current_env = await wait_for_secrets()
    _env_mtime   = SECRETS_FILE.stat().st_mtime if SECRETS_FILE.exists() else 0.0

    _pool = await create_pool(_current_env["DATABASE_URL"])
    await ensure_schema(_pool)

    t_insert   = asyncio.create_task(inserter_loop())
    t_watchdog = asyncio.create_task(secrets_watchdog())

    log.info("Application ready.")
    yield

    t_insert.cancel()
    t_watchdog.cancel()
    if _pool:
        await _pool.close()
    log.info("Application shut down.")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

app = FastAPI(title="Vault-FastAPI Demo", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/recent")
async def recent(limit: int = 10):
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, value, inserted_at FROM random_strings ORDER BY id DESC LIMIT $1",
            limit,
        )
    return [dict(r) for r in rows]


@app.get("/count")
async def count():
    async with _pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) AS total FROM random_strings")
    return {"total": row["total"]}

