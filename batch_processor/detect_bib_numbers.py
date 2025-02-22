import argparse
import asyncio
import logging

from src.config import BATCH_SIZE, DEST_FOLDER, MAX_IMAGES
from src.ocr_handler import initialize_ocr, process_images_with_ocr
from src.result_handler import save_results_to_csv
from src.s3_handler import batch_download_images, list_s3_images
from tqdm import tqdm

# Set up logging
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
    default=BATCH_SIZE,
    help="Number of images to process per batch",
)
args = parser.parse_args()


async def main():
    """Main pipeline: Downloads and processes images in parallel."""
    logger.info("Fetching images from S3...")
    image_keys = list_s3_images("s3://athlete-number", DEST_FOLDER, args.max_images)

    if not image_keys:
        logger.warning("No images found in S3 bucket.")
        return

    logger.info(
        f"Found {len(image_keys)} images. Processing in batches of {args.batch_size}..."
    )

    # Initialize OCRService once
    ocr_service = await initialize_ocr()

    # 🔥 Add a progress bar with `logger`
    with tqdm(total=len(image_keys), desc="Processing Images", unit="img") as pbar:
        pending_downloads = None

        for i in range(0, len(image_keys), args.batch_size):
            batch_keys = image_keys[i : i + args.batch_size]

            logger.info(
                f"🚀 Starting batch {i // args.batch_size + 1} ({len(batch_keys)} images)..."
            )

            # 🔥 Start downloading next batch while processing current batch
            if pending_downloads is None:
                # First batch: Start downloading immediately
                pending_downloads = asyncio.create_task(
                    batch_download_images(batch_keys)
                )
                images = await pending_downloads
            else:
                # Next batch: Start downloading while processing previous batch
                new_downloads = asyncio.create_task(batch_download_images(batch_keys))
                images = await pending_downloads  # Get previous batch's images
                pending_downloads = new_downloads  # Start new batch download

            if not images:
                logger.warning("⚠️ Skipping batch due to failed downloads.")
                continue

            # 🔥 Process images while the next batch is downloading
            detection_results = await process_images_with_ocr(ocr_service, images)
            save_results_to_csv(detection_results, batch_keys)

            # ✅ Update progress bar and log progress
            pbar.update(len(batch_keys))
            logger.info(f"✅ Processed {pbar.n}/{len(image_keys)} images.")

        # Ensure the last batch finishes downloading
        if pending_downloads:
            final_images = await pending_downloads
            if final_images:
                detection_results = await process_images_with_ocr(
                    ocr_service, final_images
                )
                save_results_to_csv(detection_results, batch_keys)
                pbar.update(len(final_images))
                logger.info(
                    f"✅ Processed final batch. Total: {pbar.n}/{len(image_keys)} images."
                )

    logger.info("🎉✅ Processing complete!")


if __name__ == "__main__":
    asyncio.run(main())
