import argparse
import asyncio

from src.config import BATCH_SIZE, DEST_FOLDER, MAX_IMAGES
from src.ocr_handler import initialize_ocr, process_images_with_ocr
from src.result_handler import save_results_to_csv
from src.s3_handler import batch_download_images, list_s3_images

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
    """Main pipeline for processing images."""
    print("Fetching images from S3...")
    image_keys = list_s3_images("s3://athlete-number", DEST_FOLDER, args.max_images)

    if not image_keys:
        print("No images found in S3 bucket.")
        return

    print(
        f"Found {len(image_keys)} images. Processing in batches of {args.batch_size}..."
    )

    # Initialize OCRService once
    ocr_service = await initialize_ocr()

    for i in range(0, len(image_keys), args.batch_size):
        batch_keys = image_keys[i : i + args.batch_size]

        print(f"\nProcessing batch {i // args.batch_size + 1}...")
        images = await batch_download_images(batch_keys)

        if not images:
            print("Skipping batch due to failed downloads.")
            continue

        detection_results = process_images_with_ocr(ocr_service, images)
        save_results_to_csv(detection_results, batch_keys)

    print("\n✅ Processing complete!")


if __name__ == "__main__":
    asyncio.run(main())
