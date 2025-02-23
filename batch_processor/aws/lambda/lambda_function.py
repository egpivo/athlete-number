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
ec2_client = boto3.client("ec2")

# Constants
CLIENT_BUCKET = os.getenv("CLIENT_BUCKET", "pc8tw.public")
DEST_BUCKET = os.getenv("DEST_BUCKET", "athlete-number-detection")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "athlete_number_detection_job_counter")
TRACKING_TABLE = os.getenv("TRACKING_TABLE", "athlete_number_detection_image_tracker")
IMAGE_THRESHOLD = int(
    os.getenv("IMAGE_THRESHOLD", 1000000)
)  # Trigger EC2 when threshold is met
EC2_INSTANCE_ID = os.getenv("EC2_INSTANCE_ID")  # Load EC2 Instance ID from .env

# Get the current date as JobID
TODAY_DATE = datetime.utcnow().strftime("%Y-%m-%d")
DEST_FOLDER = f"images/{TODAY_DATE}/"  # Organize by date
CURRENT_JOB_ID = TODAY_DATE

# Load and validate prefixes from environment variables
env_prefixes = os.getenv("PREFIXES", "").split(",")
env_prefixes = [
    p.strip() for p in env_prefixes if p.strip()
]  # Remove empty strings & spaces

logger.info(f"📂 Available environment prefixes: {env_prefixes}")


def lambda_handler(event, context):
    """Process images and only copy non-duplicate ones."""
    try:
        # Extract parameters from event payload (overrides environment prefixes)
        dry_run = event.get("dry_run", False)
        max_files = event.get("max_files", 100)

        try:
            max_files = int(max_files)  # Ensure max_files is an integer
        except ValueError:
            logger.error("❌ Invalid 'max_files' value. Must be an integer.")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"error": "Invalid 'max_files'. Must be an integer."}
                ),
            }

        event_prefixes = event.get("prefixes", None)
        processing_prefixes = (
            event_prefixes if event_prefixes else env_prefixes
        )  # Use event first, then env

        # 🚨 Stop if no valid prefixes
        if (
            not processing_prefixes
            or not isinstance(processing_prefixes, list)
            or len(processing_prefixes) == 0
        ):
            logger.error("❌ No prefixes provided. Cannot proceed.")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": "No prefixes provided. Set 'PREFIXES' in Lambda environment or pass them in event."
                    }
                ),
            }

        logger.info(
            f"📂 Processing {len(processing_prefixes)} prefix(es): {processing_prefixes}"
        )

        # **Process each prefix separately**
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
                continue  # Skip to next prefix

            image_files = [
                obj["Key"] for obj in response["Contents"] if "_tn_" in obj["Key"]
            ]
            image_files = image_files[:max_files]  # Apply ingestion limit

            logger.info(f"📸 Found {len(image_files)} images to process for {prefix}")

            # **Process each image**
            for file_key in image_files:
                dest_key = f"{DEST_FOLDER}{os.path.basename(file_key)}"

                if not dry_run:
                    copy_source = {"Bucket": CLIENT_BUCKET, "Key": file_key}
                    logger.info(f"📤 Copying {file_key} → {DEST_BUCKET}/{dest_key}")
                    s3_client.copy_object(
                        Bucket=DEST_BUCKET, Key=dest_key, CopySource=copy_source
                    )

                total_copied += 1

        logger.info(
            f"✅ Job {CURRENT_JOB_ID} completed successfully (Dry-Run: {dry_run})."
        )
        return {
            "statusCode": 200,
            "body": json.dumps(f"Job {CURRENT_JOB_ID} completed successfully."),
        }

    except Exception as e:
        logger.error(f"❌ Error during job processing: {str(e)}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps(f"Error: {str(e)}")}
