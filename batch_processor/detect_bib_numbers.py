# process_continuous.py
import argparse
import asyncio
import logging
import os

from src.ocr_handler import initialize_ocr, process_images_with_ocr
from src.result_handler import save_results_to_postgres
from src.sqlite_db_handler import (
    async_get_downloaded_not_processed,
    async_mark_keys_as_processed,
    init_sqlite_db,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Continuously OCR process already downloaded images."
    )
    parser.add_argument(
        "--cutoff_date", required=True, help="Cutoff date (e.g., 2025-03-08)"
    )
    parser.add_argument("--env", default="test", help="Environment (test/production)")
    parser.add_argument("--batch_size", type=int, default=10)
    parser.add_argument("--local_dir", default="./local_images")
    parser.add_argument(
        "--idle_wait",
        type=int,
        default=60,
        help="Wait seconds before next check if empty",
    )
    return parser.parse_args()


async def main(args):
    init_sqlite_db()
    await initialize_ocr()

    idle_checks = 0
    max_idle_checks = 5

    while True:
        rows_to_process = await async_get_downloaded_not_processed(
            args.cutoff_date, args.env
        )

        if not rows_to_process:
            idle_checks += 1
            logger.info(
                f"✅ No downloaded images pending. Idle checks: {idle_checks}/{max_idle_checks}"
            )
            if idle_checks >= max_idle_checks:
                logger.info("No images found for a long time. Exiting.")
                break
            await asyncio.sleep(args.idle_checks)
            continue
        else:
            idle_checks = 0

        batch = rows_to_process[: args.batch_size]
        image_keys, local_paths = zip(*batch)

        valid_paths = [path for path in local_paths if os.path.exists(path)]
        missing_paths = set(local_paths) - set(valid_paths)
        if missing_paths:
            logging.warning(f"Missing files: {missing_paths}")

        detection_results = await process_images_with_ocr(valid_paths)

        await asyncio.to_thread(
            save_results_to_postgres, detection_results, args.cutoff_date, args.env
        )
        await async_mark_keys_as_processed(image_keys, args.cutoff_date, args.env)

        for path in valid_paths:
            try:
                os.remove(path)
                logging.info(f"Removed {path}")
            except OSError as e:
                logging.error(f"Unable to delete {path}: {e}")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args))
