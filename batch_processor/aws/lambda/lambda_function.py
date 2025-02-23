import json
import logging
import os
from datetime import datetime

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

# Default Customer (Set "allsports" as the default)
DEFAULT_CUSTOMER_ID = "allsports"

# Get the current date
TODAY_DATE = datetime.utcnow().strftime("%Y-%m-%d")
DEST_FOLDER = f"images/{TODAY_DATE}/"

# Load and validate prefixes from environment variables
env_prefixes = os.getenv("PREFIXES", "").split(",")
env_prefixes = [p.strip() for p in env_prefixes if p.strip()]

logger.info(f"📂 Available environment prefixes: {env_prefixes}")


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


def update_customer_usage(customer_id, images_processed):
    """Update total_images_processed in DynamoDB correctly."""
    try:
        table = dynamodb.Table(CUSTOMER_USAGE_TABLE)
        response = table.update_item(
            Key={"customer_id": customer_id},
            UpdateExpression="ADD total_images_processed :inc",
            ExpressionAttributeValues={":inc": images_processed},
            ReturnValues="UPDATED_NEW",
        )
        logger.info(
            f"✅ Updated usage for '{customer_id}': {response.get('Attributes')}"
        )
    except Exception as e:
        logger.error(f"❌ Error updating customer usage: {str(e)}", exc_info=True)


def lambda_handler(event, context):
    """Process images and update customer usage."""
    try:
        # Extract parameters from event payload
        dry_run = event.get("dry_run", False)
        max_files = event.get("max_files", 100)
        customer_id = event.get("customer_id", DEFAULT_CUSTOMER_ID)

        try:
            max_files = int(max_files)
        except ValueError:
            logger.error("❌ Invalid 'max_files' value. Must be an integer.")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"error": "Invalid 'max_files'. Must be an integer."}
                ),
            }

        event_prefixes = event.get("prefixes", None)
        processing_prefixes = event_prefixes if event_prefixes else env_prefixes

        if not processing_prefixes:
            logger.error("❌ No prefixes provided. Cannot proceed.")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No prefixes provided."}),
            }

        # ✅ Fetch Customer Contract Data
        contract_data = get_customer_usage(customer_id)
        if not contract_data:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"error": "Customer contract not found. Cannot proceed."}
                ),
            }

        contract_end_date = contract_data["end_date"]
        total_images_processed = contract_data["total_images_processed"]
        contract_limit = contract_data["contract_limit"]

        contract_end_datetime = datetime.strptime(contract_end_date, "%Y-%m-%d")
        today_datetime = datetime.strptime(TODAY_DATE, "%Y-%m-%d")

        # 🚨 **Stop if contract is expired**
        if today_datetime > contract_end_datetime:
            logger.error(
                f"❌ Processing date {TODAY_DATE} exceeds contract end date {contract_end_date}."
            )
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"error": f"Contract expired on {contract_end_date}."}
                ),
            }

        # 🚨 **Stop if customer exceeded their quota**
        remaining_capacity = contract_limit - total_images_processed
        if remaining_capacity <= 0:
            logger.error(
                f"❌ Customer '{customer_id}' exceeded contract limit ({total_images_processed}/{contract_limit} images)."
            )
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Processing capacity exceeded."}),
            }

        logger.info(
            f"📂 Processing {len(processing_prefixes)} prefix(es): {processing_prefixes}"
        )

        total_copied = 0
        for prefix in processing_prefixes:
            formatted_prefix = f"WEBDATA/{prefix.strip('/')}/"
            logger.info(
                f"🔎 Listing S3 objects from {CLIENT_BUCKET} (Prefix: {formatted_prefix})"
            )
            response = s3_client.list_objects_v2(
                Bucket=CLIENT_BUCKET, Prefix=formatted_prefix
            )

            if "Contents" not in response:
                logger.warning(f"⚠ No images found for prefix {prefix}. Skipping...")
                continue

            image_files = [
                obj["Key"] for obj in response["Contents"] if "_tn_" in obj["Key"]
            ]
            image_files = image_files[:max_files]  # Limit processing to `max_files`

            logger.info(f"📸 Found {len(image_files)} images to process for {prefix}")

            processed_in_prefix = 0
            for file_key in image_files:
                # 🚨 Stop if remaining capacity is exhausted
                if remaining_capacity <= 0:
                    logger.warning(
                        f"🚨 Stopping processing. Remaining capacity: {remaining_capacity}"
                    )
                    break

                dest_key = f"{DEST_FOLDER}{os.path.basename(file_key)}"

                if not dry_run:
                    copy_source = {"Bucket": CLIENT_BUCKET, "Key": file_key}
                    logger.info(f"📤 Copying {file_key} → {DEST_BUCKET}/{dest_key}")
                    s3_client.copy_object(
                        Bucket=DEST_BUCKET, Key=dest_key, CopySource=copy_source
                    )

                total_copied += 1
                processed_in_prefix += 1
                remaining_capacity -= 1  # Reduce remaining capacity dynamically

            logger.info(f"✅ Processed {processed_in_prefix} images for prefix {prefix}")

            # 🚨 Stop processing entirely if contract limit is reached
            if remaining_capacity <= 0:
                logger.warning(f"🚨 Contract limit reached. Stopping all processing.")
                break

        if total_copied > 0 and not dry_run:
            update_customer_usage(customer_id, total_copied)

        logger.info(f"✅ Job completed successfully (Processed {total_copied} images).")
        return {
            "statusCode": 200,
            "body": json.dumps(f"Processed {total_copied} images."),
        }

    except Exception as e:
        logger.error(f"❌ Error during job processing: {str(e)}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps(f"Error: {str(e)}")}
