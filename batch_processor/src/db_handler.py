import asyncio
import logging
import os
import time

import boto3
import psycopg2
from botocore.exceptions import ClientError
from src.config import AWS_REGION, DB_CREDENTIALS, DEST_BUCKET, DEST_FOLDER

dynamodb = boto3.client("dynamodb", region_name=AWS_REGION)

OCR_BATCH_SIZE = int(os.getenv("OCR_BATCH_SIZE", 10))
CHECKPOINT_TABLE = "athlete_number_detection_image_processing_checkpoint"
PROCESSED_KEY_TABLE = "athlete_number_detection_processed_image"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_processed_keys_from_db(image_keys: list, cutoff_date: str, env: str, race_id: str = None) -> set:
    """Retrieve keys already processed from the database."""
    processed = set()
    if not image_keys:
        return processed
    try:
        conn = psycopg2.connect(**DB_CREDENTIALS)
        with conn.cursor() as cur:
            # Process in chunks to avoid query size limits
            chunk_size = 1000
            for i in range(0, len(image_keys), chunk_size):
                chunk = image_keys[i : i + chunk_size]
                placeholders = ",".join(["%s"] * len(chunk))
                if race_id:
                    query = f"SELECT image_key FROM {PROCESSED_KEY_TABLE} WHERE image_key IN ({placeholders}) AND cutoff_date = '{cutoff_date}' AND env = '{env}' AND race_id = '{race_id}'"
                else:
                    query = f"SELECT image_key FROM {PROCESSED_KEY_TABLE} WHERE image_key IN ({placeholders}) AND cutoff_date = '{cutoff_date}' AND env = '{env}'"
                cur.execute(query, chunk)
                processed.update(row[0] for row in cur.fetchall())
        conn.close()
    except Exception as e:
        logger.error(f"Error fetching processed keys: {e}")
    return processed


def mark_keys_as_processed(image_keys: list, cutoff_date: str, env: str, race_id: str) -> None:
    """Mark keys as processed in the database with a cutoff date."""
    if not image_keys:
        return
    try:
        image_keys = set(image_keys)
        conn = psycopg2.connect(**DB_CREDENTIALS)
        with conn.cursor() as cur:
            # Use executemany with ON CONFLICT to handle duplicates
            args = [
                (key, cutoff_date, env, race_id) for key in image_keys
            ]  # ✅ Include cutoff_date
            if race_id:
                cur.executemany(
                    f"""INSERT INTO {PROCESSED_KEY_TABLE} (image_key, cutoff_date, env, race_id)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (image_key, cutoff_date, env) DO NOTHING""",
                    args,
                )
            else:            
                cur.executemany(
                    f"""INSERT INTO {PROCESSED_KEY_TABLE} (image_key, cutoff_date, env)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (image_key, cutoff_date, env) DO NOTHING""",
                    args,
                 )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Error marking keys as processed: {e}")


def get_last_checkpoint(cutoff_date):
    """Fetches the last processed image key from DynamoDB."""
    try:
        response = dynamodb.get_item(
            TableName=CHECKPOINT_TABLE,
            Key={"bucket_name": {"S": f"{DEST_BUCKET}/{DEST_FOLDER}/{cutoff_date}"}},
        )
        return response.get("Item", {}).get("last_processed_key", {}).get("S")
    except ClientError as e:
        logger.error(f"❌ DynamoDB error: {e}")
        return None


async def async_write_checkpoint_safely(new_checkpoint, cutoff_date):
    try:
        response = await asyncio.to_thread(
            dynamodb.update_item,
            TableName=CHECKPOINT_TABLE,
            Key={"bucket_name": {"S": f"{DEST_BUCKET}/{DEST_FOLDER}/{cutoff_date}"}},
            UpdateExpression="SET last_processed_key = :new_checkpoint, updated_at = :ts",
            ExpressionAttributeValues={
                ":new_checkpoint": {"S": new_checkpoint},
                ":ts": {"N": str(int(time.time()))},
            },
            ConditionExpression="attribute_exists(bucket_name) OR attribute_not_exists(last_processed_key)",
        )
        logger.info(f"✅ Checkpoint updated: {new_checkpoint}")
    except ClientError as e:
        logger.error(f"❌ Checkpoint update error: {e}")


async def async_get_last_checkpoint(cutoff_date):
    return await asyncio.to_thread(get_last_checkpoint, cutoff_date)


async def async_get_processed_keys_from_db(image_keys, cutoff_date, env, race_id):
    return await asyncio.to_thread(
        get_processed_keys_from_db, image_keys, cutoff_date, env, race_id
    )


async def async_mark_keys_as_processed(image_keys, cutoff_date, env, race_id):
    await asyncio.to_thread(mark_keys_as_processed, image_keys, cutoff_date, env, race_id)
