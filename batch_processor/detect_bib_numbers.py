import argparse
import asyncio
import logging
import os

from src.config import DEST_BUCKET, DEST_FOLDER, MAX_IMAGES
from src.db_handler import (
    async_get_last_checkpoint,
    async_get_processed_keys_from_db,
    async_mark_keys_as_processed,
    async_write_checkpoint_safely,
)
from src.ocr_handler import initialize_ocr, process_images_with_ocr
from src.result_handler import save_results_to_csv, save_results_to_postgres
from src.s3_handler import batch_download_images, list_s3_images_incremental
from tqdm import tqdm

OCR_BATCH_SIZE = int(os.getenv("OCR_BATCH_SIZE", 10))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Batch process images from S3")
parser.add_argument(
    "--max_images",
    type=int,
    default=MAX_IMAGES,
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
args = parser.parse_args()


async def main():
    """Main pipeline for processing images incrementally."""
    logger.info("🚀 Starting incremental image processing...")

    # ✅ Read last checkpoint
    last_processed_key = await async_get_last_checkpoint(args.cutoff_date)
    logger.info(f"🔄 Resuming from checkpoint: {last_processed_key or 'Beginning'}")

    # ✅ List images from S3 after the last checkpoint
    image_keys, next_start_after = await asyncio.to_thread(
        list_s3_images_incremental,
        DEST_BUCKET,
        f"{DEST_FOLDER}/{args.cutoff_date}",
        last_processed_key,
        args.max_images,
    )

    if not image_keys:
        logger.info("✅ No new images to process.")
        return

    # ✅ Filter out already processed keys using async database call
    processed_keys = await async_get_processed_keys_from_db(
        image_keys, args.cutoff_date
    )
    processed_keys = set(processed_keys)
    unprocessed_keys = [key for key in image_keys if key not in processed_keys]

    if not unprocessed_keys:
        logger.info("✅ All new images already processed. Updating checkpoint.")
        new_checkpoint = max(image_keys) if image_keys else last_processed_key
        await async_write_checkpoint_safely(new_checkpoint, args.cutoff_date)
        return

    logger.info(
        f"📸 Processing {len(unprocessed_keys)} new images in batches of {args.batch_size}..."
    )
    ocr_service = await initialize_ocr()
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

            # ✅ Process images asynchronously
            detection_results = await process_images_with_ocr(ocr_service, images)
            await asyncio.to_thread(save_results_to_csv, detection_results)
            await asyncio.to_thread(
                save_results_to_postgres, detection_results, args.cutoff_date, args.env
            )

            # ✅ Mark keys as processed & update checkpoint asynchronously
            await async_mark_keys_as_processed(batch_keys, args.cutoff_date)
            new_checkpoint = batch_keys[-1]
            await async_write_checkpoint_safely(new_checkpoint, args.cutoff_date)

            pbar.update(len(batch_keys))
            logger.info(
                f"✅ Processed {pbar.n}/{len(unprocessed_keys)} images. Checkpoint: {new_checkpoint}"
            )

    logger.info("🎉✅ Incremental processing complete!")


if __name__ == "__main__":
    asyncio.run(main())
