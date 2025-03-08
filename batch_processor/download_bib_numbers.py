import argparse
import asyncio
import logging
import os

from src.config import DEST_BUCKET, DEST_FOLDER
from src.s3_handler import batch_download_images, list_s3_images_incremental
from src.sqlite_db_handler import (
    async_get_last_checkpoint,
    async_mark_keys_as_downloaded,
    async_write_checkpoint,
    init_sqlite_db,
)

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        "Example script that uses SQLite for checkpointing"
    )
    parser.add_argument("--cutoff_date", required=True, help="e.g. 2025-03-08")
    parser.add_argument("--env", default="test", help="Environment (test/production)")
    parser.add_argument("--page_size", type=int, default=1000)
    parser.add_argument("--force_start", action="store_true")
    parser.add_argument("--local_dir", default="./local_images")
    return parser.parse_args()


async def main(args):
    init_sqlite_db()
    os.makedirs(args.local_dir, exist_ok=True)

    last_processed_key = None
    if not args.force_start:
        last_processed_key = await async_get_last_checkpoint(args.cutoff_date, args.env)
        logging.info(f"Last checkpoint: {last_processed_key or 'None'}")

    async for image_keys, next_start_after in list_s3_images_incremental(
        bucket=DEST_BUCKET,
        prefix=f"{DEST_FOLDER}/{args.cutoff_date}",
        last_processed_key=last_processed_key,
        batch_size=args.page_size,
    ):
        if not image_keys:
            logger.info("No more images to download.")
            break

        logger.info(f"Downloading {len(image_keys)} images...")
        downloaded = await batch_download_images(image_keys, args.local_dir)

        if not downloaded:
            logger.warning("No images downloaded.")
            continue

        local_keys = [key for key, path in downloaded]

        # Mark downloaded in SQLite DB
        await async_mark_keys_as_downloaded(local_keys, args.cutoff_date, args.env)

        # Update checkpoint after successful download
        last_key_in_batch = local_keys[-1]
        await async_write_checkpoint(args.cutoff_date, args.env, last_key_in_batch)
        logging.info(f"Checkpoint updated to {last_key_in_batch}")

        logging.info(f"✅ Batch downloaded and tracked: {len(local_keys)} images.")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args))
