import argparse
import asyncio
import logging
import os

from src.config import DEST_BUCKET, DEST_FOLDER
from src.db_handler import (
    async_get_last_checkpoint,
    async_get_processed_keys_from_db,
    async_mark_keys_as_processed,
    async_write_checkpoint_safely,
)
from src.ocr_handler import initialize_ocr, process_images_with_ocr
from src.result_handler import save_results_to_postgres
from src.s3_handler import batch_download_images, list_s3_images_incremental
from tqdm import tqdm

OCR_BATCH_SIZE = int(os.getenv("OCR_BATCH_SIZE", 10))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


import re


def get_valid_keys(s3_keys, valid_min=2335962, valid_max=2344339, processed_keys=None):
    filtered_keys = []

    for key in s3_keys:
        match = re.search(r"_(\d+)_", key)  # Extract numeric part between underscores
        if match:
            photo_number = int(match.group(1))  # Convert to integer
            if valid_min <= photo_number <= valid_max:
                filtered_keys.append(key)

    # Exclude already processed keys
    unprocessed_keys = (
        [key for key in filtered_keys if key not in processed_keys]
        if processed_keys
        else filtered_keys
    )

    return unprocessed_keys


parser = argparse.ArgumentParser(description="Batch process images from S3")
parser.add_argument(
    "--max_images",
    type=int,
    default=None,
    help="Maximum number of images to process",
)
parser.add_argument(
    "--batch_size",
    type=int,
    default=OCR_BATCH_SIZE,
    help="Number of images to process per batch",
)
parser.add_argument(
    "--cutoff_date",
    type=str,
    help="Processing date",
)
parser.add_argument(
    "--env",
    type=str,
    default="test",
    help="Environment",
)
parser.add_argument(
    "--force_start",
    action="store_true",
    help="Force restart the process by resetting the last checkpoint.",
)
parser.add_argument(
    "--race_id",
    type=str,
    default=None,
    help="Race ID",
)
args = parser.parse_args()


async def main():
    """Main pipeline for processing all images in batches."""
    logger.info("🚀 Starting incremental image processing...")

    last_processed_key = (
        None if args.force_start else await async_get_last_checkpoint(args.cutoff_date)
    )
    if args.force_start:
        logger.info("🚀 Force restart enabled. Starting from the beginning...")
    else:
        logger.info(f"🔄 Resuming from checkpoint: {last_processed_key or 'Beginning'}")

    ocr_service = await initialize_ocr()
    total_processed = 0

    async for image_keys, next_start_after in list_s3_images_incremental(
        DEST_BUCKET, f"{DEST_FOLDER}/{args.cutoff_date}", last_processed_key, 1000
    ):
        if not image_keys:
            logger.info("✅ No new images left to process.")
            break

        filtered_keys = [key for key in image_keys if "_tn_" in key]
        processed_keys = await async_get_processed_keys_from_db(
            image_keys, args.cutoff_date, args.env, args.race_id
        )
        processed_keys = set(str(key) for key in processed_keys)

        unprocessed_keys = (
            [key for key in filtered_keys if key not in processed_keys]
            if processed_keys
            else filtered_keys
        )

        if args.max_images:
            remaining = args.max_images - total_processed
            if remaining <= 0:
                logger.info("✅ Reached max images limit. Stopping.")
                break
            unprocessed_keys = unprocessed_keys[:remaining]

        if not unprocessed_keys:
            logger.info(
                "✅ All new images in this batch are already processed. Updating checkpoint."
            )
            await async_write_checkpoint_safely(next_start_after, args.cutoff_date)
            continue

        logger.info(
            f"📸 Processing {len(unprocessed_keys)} new images in batches of {args.batch_size}..."
        )
        total_batches = (len(unprocessed_keys) + args.batch_size - 1) // args.batch_size

        with tqdm(
            total=len(unprocessed_keys), desc="Processing Images", unit="img"
        ) as pbar:
            for batch_idx in range(total_batches):
                start = batch_idx * args.batch_size
                end = min((batch_idx + 1) * args.batch_size, len(unprocessed_keys))
                batch_keys = unprocessed_keys[start:end]

                # ✅ Download images concurrently (non-blocking)
                images = await batch_download_images(batch_keys)
                if not images:
                    logger.warning(
                        f"⚠️ Skipping batch {batch_idx + 1}/{total_batches} due to download errors."
                    )
                    continue

                # Process images asynchronously
                detection_results = await process_images_with_ocr(ocr_service, images)
                await asyncio.to_thread(
                    save_results_to_postgres,
                    detection_results,
                    args.cutoff_date,
                    args.env,
                    args.race_id,
                )

                # Mark keys as processed & update checkpoint asynchronously
                await async_mark_keys_as_processed(
                    batch_keys, args.cutoff_date, args.env, args.race_id
                )
                await async_write_checkpoint_safely(batch_keys[-1], args.cutoff_date)
                total_processed += len(batch_keys)
                pbar.update(len(batch_keys))
                logger.info(
                    f"Processed {pbar.n}/{len(unprocessed_keys)} images. Checkpoint: {batch_keys[-1]}"
                )
            if args.max_images is not None and total_processed >= args.max_images:
                logger.info(
                    f"Stopping early: Processed {total_processed} images (max {args.max_images})"
                )
                break
        if args.max_images is not None and total_processed >= args.max_images:
            logger.info(
                f"Stopping early: Processed {total_processed} images (max {args.max_images})"
            )
            break
    logger.info("Incremental processing complete!")


if __name__ == "__main__":
    asyncio.run(main())
