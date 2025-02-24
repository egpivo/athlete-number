import argparse
import asyncio
import logging
import os

from src.config import DEST_BUCKET, DEST_FOLDER, MAX_IMAGES
from src.ocr_handler import initialize_ocr, process_images_with_ocr
from src.result_handler import save_results_to_csv
from src.s3_handler import batch_download_images, list_s3_images
from tqdm import tqdm

OCR_BATCH_SIZE = int(os.getenv("OCR_BATCH_SIZE", 10))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Parse command-line arguments
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
args = parser.parse_args()


async def main():
    """Main pipeline for processing images."""
    logger.info("Fetching images from S3...")

    # ✅ Ensure max_images limit is respected
    image_keys = list_s3_images(DEST_BUCKET, DEST_FOLDER, args.max_images)

    if not image_keys:
        logger.warning("⚠️ No images found in S3 bucket.")
        return

    logger.info(
        f"✅ Found {len(image_keys)} images. Processing in batches of {args.batch_size}..."
    )

    ocr_service = await initialize_ocr()

    total_batches = (len(image_keys) + args.batch_size - 1) // args.batch_size

    with tqdm(total=len(image_keys), desc="Processing Images", unit="img") as pbar:
        for batch_index in range(total_batches):
            start = batch_index * args.batch_size
            end = min((batch_index + 1) * args.batch_size, len(image_keys))
            batch_keys = image_keys[start:end]

            logger.info(
                f"🚀 Starting batch {batch_index + 1}/{total_batches} ({len(batch_keys)} images)..."
            )

            images = await batch_download_images(batch_keys)

            if not images:
                logger.warning("⚠️ Skipping batch due to failed downloads.")
                continue

            # ✅ Process the downloaded batch
            detection_results = await process_images_with_ocr(ocr_service, images)
            save_results_to_csv(detection_results, batch_keys)

            pbar.update(len(batch_keys))
            logger.info(f"✅ Processed {pbar.n}/{len(image_keys)} images.")

        logger.info("🎉✅ Processing complete!")


if __name__ == "__main__":
    asyncio.run(main())
