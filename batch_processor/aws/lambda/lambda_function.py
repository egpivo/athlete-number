import json
import logging
import os
from datetime import datetime, timezone

import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS Clients
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# Constants
CLIENT_BUCKET = os.getenv("CLIENT_BUCKET", "pc8tw.public")
DEST_BUCKET = os.getenv("DEST_BUCKET", "athlete-number-detection")
CUSTOMER_USAGE_TABLE = os.getenv(
    "CUSTOMER_USAGE_TABLE", "athlete_number_detection_customer_usage"
)
JOB_COUNTER_TABLE = "athlete_number_detection_job_counter"
IMAGE_TRACKER_TABLE = "athlete_number_detection_image_tracker"

# Default Customer
DEFAULT_CUSTOMER_ID = "allsports"

# Get the current date
TODAY_DATE = datetime.utcnow().strftime("%Y-%m-%d")
DEST_FOLDER = f"images/{TODAY_DATE}/"

# Load and validate prefixes from environment variables
env_prefixes = os.getenv("PREFIXES", "").split(",")
env_prefixes = [p.strip() for p in env_prefixes if p.strip()]

logger.info(f"📂 Available environment prefixes: {env_prefixes}")

# Batch threshold before triggering a new job
BATCH_SIZE = 10000


def get_customer_usage(customer_id):
    """Fetch the customer's contract details from DynamoDB."""
    try:
        table = dynamodb.Table(CUSTOMER_USAGE_TABLE)
        response = table.get_item(Key={"customer_id": customer_id})

        if "Item" not in response:
            logger.error(f"❌ No contract data found for customer '{customer_id}'.")
            return None

        contract_data = response["Item"]
        return {
            "end_date": contract_data.get("end_date"),
            "total_images_processed": int(
                contract_data.get("total_images_processed", 0)
            ),
            "contract_limit": int(contract_data.get("contract_limit", 0)),
        }

    except Exception as e:
        logger.error(f"❌ Error fetching contract data: {str(e)}", exc_info=True)
        return None


def get_next_job_id(customer_id, today_date):
    """Retrieve the next available job_id for today."""
    try:
        table = dynamodb.Table(JOB_COUNTER_TABLE)

        # Fetch all job_ids for today
        response = table.scan(
            FilterExpression="customer_id = :cid AND begins_with(job_id, :date_prefix)",
            ExpressionAttributeValues={":cid": customer_id, ":date_prefix": today_date},
        )

        existing_jobs = sorted([item["job_id"] for item in response.get("Items", [])])

        if not existing_jobs:
            return f"{today_date}-01"

        last_job_id = existing_jobs[-1]
        last_batch_number = int(last_job_id.split("-")[-1])
        next_batch_number = last_batch_number + 1

        return f"{today_date}-{next_batch_number:02d}"

    except Exception as e:
        logger.error(f"❌ Error retrieving job_id: {str(e)}", exc_info=True)
        return f"{today_date}-01"


def update_customer_usage(customer_id, images_processed):
    """Update total_images_processed and modified_at timestamp in DynamoDB."""
    try:
        table = dynamodb.Table(CUSTOMER_USAGE_TABLE)
        current_timestamp = datetime.now(timezone.utc).isoformat()

        # Step 1: Ensure `images_processed` is an integer
        if not isinstance(images_processed, int):
            logger.error(
                f"❌ images_processed must be an integer, received: {type(images_processed)}"
            )
            return

        # Step 2: Increment `total_images_processed`
        response = table.update_item(
            Key={"customer_id": customer_id},
            UpdateExpression="ADD total_images_processed :inc",
            ExpressionAttributeValues={
                ":inc": images_processed  # Ensuring it's an integer
            },
            ReturnValues="UPDATED_NEW",
        )

        logger.info(
            f"✅ Updated usage for '{customer_id}': {response.get('Attributes')}"
        )

        # Step 3: Update `modified_at` separately
        response = table.update_item(
            Key={"customer_id": customer_id},
            UpdateExpression="SET modified_at = :timestamp",
            ExpressionAttributeValues={
                ":timestamp": current_timestamp  # Store as a string (`S` type)
            },
            ReturnValues="UPDATED_NEW",
        )

        logger.info(f"✅ Updated modified_at timestamp for '{customer_id}'")

    except Exception as e:
        logger.error(f"❌ Error updating customer usage: {str(e)}", exc_info=True)


def update_image_tracker(image_id, customer_id, file_key, job_id):
    """Insert an image tracking record into DynamoDB."""
    try:
        table = dynamodb.Table(IMAGE_TRACKER_TABLE)
        current_timestamp = datetime.now(timezone.utc).isoformat()
        table.put_item(
            Item={
                "image_id": image_id,
                "customer_id": customer_id,
                "file_key": file_key,
                "timestamp": current_timestamp,
                "job_id": job_id,
            }
        )
        logger.info(f"✅ Image tracking recorded for {image_id}")
    except Exception as e:
        logger.error(f"❌ Error updating image tracker: {str(e)}", exc_info=True)


def update_job_counter(customer_id, job_id, images_processed):
    """Ensure job counter exists and update total_images_processed with modified timestamp."""
    try:
        table = dynamodb.Table("athlete_number_detection_job_counter")
        current_timestamp = datetime.now(timezone.utc).isoformat()

        # Ensure `images_processed` is an integer
        if not isinstance(images_processed, int):
            logger.error(
                f"❌ images_processed must be an integer, received: {type(images_processed)}"
            )
            return

        # Step 1: Ensure job exists
        response = table.get_item(Key={"customer_id": customer_id, "job_id": job_id})
        if "Item" not in response:
            logger.info(
                f"⚠️ Job '{job_id}' for customer '{customer_id}' not found. Creating a new entry."
            )
            table.put_item(
                Item={
                    "customer_id": customer_id,
                    "job_id": job_id,
                    "total_images_processed": 0,
                    "modified_at": current_timestamp,
                }
            )

        # Step 2: Update job counter and timestamp
        response = table.update_item(
            Key={"customer_id": customer_id, "job_id": job_id},
            UpdateExpression="ADD total_images_processed :inc SET modified_at = :timestamp",
            ExpressionAttributeValues={
                ":inc": images_processed,  # Ensure this is an integer
                ":timestamp": current_timestamp,  # Store as a string (`S` type)
            },
            ReturnValues="UPDATED_NEW",
        )

        logger.info(
            f"✅ Updated job counter for '{customer_id}' - Job '{job_id}': {response.get('Attributes')}"
        )
    except Exception as e:
        logger.error(f"❌ Error updating job counter: {str(e)}", exc_info=True)


def lambda_handler(event, context):
    """Process images and update customer usage, image tracker, and job counter."""
    try:
        dry_run = event.get("dry_run", False)
        max_files = event.get("max_files", 100)
        customer_id = event.get("customer_id", DEFAULT_CUSTOMER_ID)

        event_prefixes = event.get("prefixes", None)
        processing_prefixes = event_prefixes if event_prefixes else env_prefixes

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
        job_id = get_next_job_id(customer_id, TODAY_DATE)

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
            image_files = image_files[:max_files]

            for file_key in image_files:
                if remaining_capacity <= 0:
                    break

                dest_key = f"{DEST_FOLDER}{os.path.basename(file_key)}"

                if not dry_run:
                    s3_client.copy_object(
                        Bucket=DEST_BUCKET,
                        Key=dest_key,
                        CopySource={"Bucket": CLIENT_BUCKET, "Key": file_key},
                    )
                    update_image_tracker(
                        os.path.basename(file_key), customer_id, file_key, job_id
                    )

                total_copied += 1
                remaining_capacity -= 1

                if total_copied % BATCH_SIZE == 0:
                    job_id = get_next_job_id(customer_id, TODAY_DATE)

        if total_copied > 0 and not dry_run:
            update_customer_usage(customer_id, total_copied)
            update_job_counter(customer_id, job_id, total_copied)

        return {
            "statusCode": 200,
            "body": json.dumps(f"Processed {total_copied} images."),
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps(f"Error: {str(e)}")}
