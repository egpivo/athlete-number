# sqlite_db_handler.py

import asyncio
import logging
import sqlite3

logger = logging.getLogger(__name__)

DB_PATH = "pipeline.db"


def init_sqlite_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Existing table(s) for downloaded images, etc.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS downloaded_images (
            image_key TEXT NOT NULL,
            cutoff_date TEXT NOT NULL,
            env TEXT NOT NULL,
            downloaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (image_key, cutoff_date, env)
        )
        """
    )

    # -- Now create a separate checkpoint table --
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ingestion_checkpoint (
            cutoff_date TEXT NOT NULL,
            env TEXT NOT NULL,
            last_processed_key TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (cutoff_date, env)
        )
        """
    )

    conn.commit()
    conn.close()
    logger.info("SQLite tables initialized.")


def get_last_checkpoint(cutoff_date, env):
    """
    Returns the 'last_processed_key' for a given (cutoff_date, env) if present,
    else returns None.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT last_processed_key
        FROM ingestion_checkpoint
        WHERE cutoff_date = ? AND env = ?
        LIMIT 1
        """,
        (cutoff_date, env),
    )
    row = cur.fetchone()
    conn.close()

    if row:
        return row[0]  # last_processed_key
    return None


def write_checkpoint_safely(new_checkpoint, cutoff_date, env):
    """
    Updates or inserts the last_processed_key for the given (cutoff_date, env).
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # We can do an "INSERT OR REPLACE" approach, or handle upsert logic
    cur.execute(
        """
        INSERT INTO ingestion_checkpoint (cutoff_date, env, last_processed_key, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (cutoff_date, env)
        DO UPDATE SET
            last_processed_key = excluded.last_processed_key,
            updated_at = excluded.updated_at
        """,
        (cutoff_date, env, new_checkpoint),
    )

    conn.commit()
    conn.close()
    logger.info(
        f"Checkpoint updated to {new_checkpoint} for cutoff_date={cutoff_date}, env={env}"
    )


async def async_get_last_checkpoint(cutoff_date, env):
    return await asyncio.to_thread(get_last_checkpoint, cutoff_date, env)


async def async_write_checkpoint_safely(new_checkpoint, cutoff_date, env):
    return await asyncio.to_thread(
        write_checkpoint_safely, new_checkpoint, cutoff_date, env
    )
