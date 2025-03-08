# sqlite_db_handler.py

import asyncio
import logging
import sqlite3

logger = logging.getLogger(__name__)

DB_PATH = "pipeline.db"


def init_sqlite_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Downloaded images table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS downloaded_images (
            image_key TEXT NOT NULL,
            cutoff_date TEXT NOT NULL,
            env TEXT NOT NULL,
            local_path TEXT NOT NULL,
            downloaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (image_key, cutoff_date, env)
        )
        """
    )

    # Processed images table (missing earlier)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_images (
            image_key TEXT NOT NULL,
            cutoff_date TEXT NOT NULL,
            env TEXT NOT NULL,
            processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (image_key, cutoff_date, env)
        )
        """
    )

    # Checkpoint table
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


async def async_get_last_checkpoint(cutoff_date, env):
    def db_query():
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT last_processed_key FROM ingestion_checkpoint WHERE cutoff_date=? AND env=?",
            (cutoff_date, env),
        )
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    return await asyncio.to_thread(db_query)


async def async_write_checkpoint(cutoff_date, env, last_processed_key):
    def db_update():
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO ingestion_checkpoint (cutoff_date, env, last_processed_key, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(cutoff_date, env) DO UPDATE SET
                last_processed_key=excluded.last_processed_key,
                updated_at=CURRENT_TIMESTAMP
            """,
            (cutoff_date, env, last_processed_key),
        )
        conn.commit()
        conn.close()

    await asyncio.to_thread(db_update)


def mark_keys_as_downloaded(
    image_keys: list, local_paths: list, cutoff_date: str, env: str
):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT OR IGNORE INTO downloaded_images (image_key, cutoff_date, env, local_path)
        VALUES (?, ?, ?, ?)
        """,
        [(key, cutoff_date, env, path) for key, path in zip(image_keys, local_paths)],
    )
    conn.commit()
    conn.close()


async def async_mark_keys_as_downloaded(
    image_keys: list, local_paths: list, cutoff_date: str, env: str
):
    await asyncio.to_thread(
        mark_keys_as_downloaded, image_keys, local_paths, cutoff_date, env
    )


async def async_mark_keys_as_processed(image_keys, cutoff_date, env):
    def db_update():
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT OR IGNORE INTO processed_images(image_key, cutoff_date, env, processed_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [(key, cutoff_date, env) for key in image_keys],
        )
        conn.commit()
        conn.close()

    await asyncio.to_thread(db_update)


async def async_get_downloaded_not_processed(cutoff_date, env):
    def db_query():
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        query = """
            SELECT d.image_key, d.local_path
            FROM downloaded_images d
            LEFT JOIN processed_images p
              ON d.image_key = p.image_key AND d.cutoff_date = p.cutoff_date AND d.env = p.env
            WHERE d.cutoff_date = ? AND d.env = ? AND p.image_key IS NULL
            ORDER BY d.downloaded_at ASC
        """
        cur.execute(query, (cutoff_date, env))
        rows = cur.fetchall()
        conn.close()
        return rows

    return await asyncio.to_thread(db_query)
