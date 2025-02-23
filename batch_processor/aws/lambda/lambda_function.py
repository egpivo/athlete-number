import json
import logging

from src.config import (
    BATCH_SIZE,
    CLIENT_BUCKET,
    DEFAULT_CUSTOMER_ID,
    DEST_BUCKET,
    DEST_FOLDER,
    ENV_PREFIXES,
    TODAY_DATE,
    os,
)
from src.dynamodb_utils import (
    get_customer_usage,
    get_next_job_id,
    is_duplicate_image,
    update_customer_usage,
    update_image_tracker,
    update_job_counter,
)
from src.s3_utils import s3_client

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Process images and update customer usage, image tracker, and job counter."""
    try:
        dry_run = event.get("dry_run", False)
        max_files = event.get("max_files", 100)
        customer_id = event.get("customer_id", DEFAULT_CUSTOMER_ID)

        event_prefixes = event.get("prefixes", None)
        processing_prefixes = event_prefixes if event_prefixes else ENV_PREFIXES

        if not processing_prefixes:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No prefixes provided."}),
            }

        contract_data = get_customer_usage(customer_id)
        if not contract_data:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Customer contract not found."}),
            }

        remaining_capacity = (
            contract_data["contract_limit"] - contract_data["total_images_processed"]
        )
        if remaining_capacity <= 0:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Processing capacity exceeded."}),
            }

        logger.info(
            f"📂 Processing {len(processing_prefixes)} prefix(es): {processing_prefixes}"
        )

        total_copied = 0
        job_id = get_next_job_id(customer_id, TODAY_DATE, BATCH_SIZE)

        for prefix in processing_prefixes:
            formatted_prefix = f"WEBDATA/{prefix.strip('/')}/"
            response = s3_client.list_objects_v2(
                Bucket=CLIENT_BUCKET, Prefix=formatted_prefix
            )

            if "Contents" not in response:
                continue

            image_files = [
                obj["Key"] for obj in response["Contents"] if "_tn_" in obj["Key"]
            ]

            remaining_files = max_files - total_copied
            if remaining_files <= 0:
                break

            image_files = image_files[:remaining_files]

            for file_key in image_files:
                if total_copied >= max_files or remaining_capacity <= 0:
                    break

                image_id = os.path.basename(file_key)  # Extract image_id

                if is_duplicate_image(customer_id, image_id):
                    logger.info(f"⚠️ Skipping duplicate file: {file_key}")
                    continue

                dest_key = f"{DEST_FOLDER}{image_id}"

                if not dry_run:
                    s3_client.copy_object(
                        Bucket=DEST_BUCKET,
                        Key=dest_key,
                        CopySource={"Bucket": CLIENT_BUCKET, "Key": file_key},
                    )
                    update_image_tracker(image_id, customer_id, file_key, job_id)

                total_copied += 1
                remaining_capacity -= 1

                if total_copied % BATCH_SIZE == 0:
                    job_id = get_next_job_id(customer_id, TODAY_DATE, BATCH_SIZE)

        if total_copied > 0 and not dry_run:
            update_customer_usage(customer_id, total_copied)
            update_job_counter(customer_id, job_id, total_copied, BATCH_SIZE)

        return {
            "statusCode": 200,
            "body": json.dumps(f"Processed {total_copied} images."),
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps(f"Error: {str(e)}")}
