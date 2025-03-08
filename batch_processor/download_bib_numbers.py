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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download images with size limit and checkpoint."
    )
    parser.add_argument("--cutoff_date", required=True, help="e.g., 2025-03-08")
    parser.add_argument("--env", default="test", help="Environment (test/production)")
    parser.add_argument("--batch_size", type=int, default=50)
    parser.add_argument(
        "--max_images", type=int, default=None, help="Max total images to download"
    )
    parser.add_argument("--local_dir", default="./local_images")
    parser.add_argument("--force_start", action="store_true")
    return parser.parse_args()


async def main(args):
    init_sqlite_db()
    os.makedirs(args.local_dir, exist_ok=True)

    last_processed_key = None
    if not args.force_start:
        last_processed_key = await async_get_last_checkpoint(args.cutoff_date, args.env)
        logger.info(f"Last checkpoint: {last_processed_key or 'None'}")
    else:
        last_processed_key = None
        logger.info("Force start enabled. Ignoring checkpoint.")

    total_downloaded = 0

    async for image_keys, next_start_after in list_s3_images_incremental(
        bucket=DEST_BUCKET,
        prefix=f"{DEST_FOLDER}/{args.cutoff_date}",
        last_processed_key=last_processed_key,
        batch_size=args.batch_size,
    ):
        if not image_keys:
            logger.info("No more images to download.")
            break

        if args.max_images:
            remaining = args.max_images - total_downloaded
            if remaining <= 0:
                logger.info("✅ Reached max images limit. Stopping.")
                break
            image_keys = image_keys[:remaining]

        logger.info(f"Downloading batch of {len(image_keys)} images...")
        downloaded = await batch_download_images(image_keys, args.local_dir)

        if not downloaded:
            logger.warning("No images downloaded in this batch.")
            continue

        local_keys = [key for key, path in downloaded]

        # Mark downloaded images in SQLite DB
        await async_mark_keys_as_downloaded(local_keys, args.cutoff_date, args.env)

        # Update checkpoint
        last_processed_key = local_keys[-1]
        await async_write_checkpoint(args.cutoff_date, args.env, last_processed_key)
        logger.info(f"Checkpoint updated to {last_processed_key}")

        total_downloaded += len(local_keys)
        logger.info(f"✅ Total downloaded: {total_downloaded}")

    logger.info("All done!")


if __name__ == "__main__":
    args = parse_args()
    init_sqlite_db()
    asyncio.run(main(args))
