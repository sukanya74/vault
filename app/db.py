"""
db.py — Database connection pool management.
Reads DATABASE_URL from the Vault Agent rendered secrets file.
Retries connection until PostgreSQL is ready.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import asyncpg

log = logging.getLogger("db")

SECRETS_FILE        = Path(os.getenv("SECRETS_FILE", "/run/secrets/app.env"))
SECRETS_POLL        = int(os.getenv("SECRETS_POLL_INTERVAL", "5"))
DB_RETRY_DELAY      = int(os.getenv("DB_CONNECT_RETRY_DELAY", "3"))


# ---------------------------------------------------------------------------
# Secret file helpers
# ---------------------------------------------------------------------------

def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a KEY=VALUE file, skipping comments and blank lines."""
    env: dict[str, str] = {}
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
    return env


async def wait_for_secrets() -> dict[str, str]:
    """Block until the secrets file exists and contains DATABASE_URL."""
    log.info("Waiting for secrets file: %s", SECRETS_FILE)
    while True:
        env = parse_env_file(SECRETS_FILE)
        if env.get("DATABASE_URL"):
            log.info("Secrets loaded.")
            return env
        log.warning("Secrets not ready — retrying in %ds", SECRETS_POLL)
        await asyncio.sleep(SECRETS_POLL)


# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------

async def create_pool(database_url: str) -> asyncpg.Pool:
    """Create an asyncpg pool, retrying until PostgreSQL accepts connections."""
    attempt = 0
    while True:
        attempt += 1
        try:
            pool = await asyncpg.create_pool(
                dsn=database_url,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            log.info("DB pool established (attempt %d).", attempt)
            return pool
        except Exception as exc:
            log.warning("DB not ready (attempt %d): %s — retry in %ds", attempt, exc, DB_RETRY_DELAY)
            await asyncio.sleep(DB_RETRY_DELAY)


async def ensure_schema(pool: asyncpg.Pool) -> None:
    """Create required tables if they don't exist."""
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS random_strings (
                id          BIGSERIAL    PRIMARY KEY,
                value       TEXT         NOT NULL,
                inserted_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_rs_id_desc ON random_strings (id DESC);
        """)
    log.info("Schema ready.")

