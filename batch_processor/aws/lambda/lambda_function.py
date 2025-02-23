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
TODAY_DATE = datetime.utcnow().strftime("%Y-%m-%d")  # Get current date (UTC)
DEST_FOLDER = f"images/{TODAY_DATE}/"  # Organize by date
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "JobImageCounter")
TRACKING_TABLE = os.getenv(
    "TRACKING_TABLE", "athlete_number_detection_image_ingestion_tracker"
)
IMAGE_THRESHOLD = int(
    os.getenv("IMAGE_THRESHOLD", 1_000_000)
)  # Trigger EC2 when this is reached
EC2_INSTANCE_ID = os.getenv("EC2_INSTANCE_ID")  # Load EC2 Instance ID from .env

# Get the current date as JobID
CURRENT_JOB_ID = TODAY_DATE


def image_already_copied(file_key: str) -> bool:
    """Check if an image has already been copied by looking it up in DynamoDB."""
    table = dynamodb.Table(TRACKING_TABLE)
    response = table.get_item(Key={"FileKey": file_key})
    return "Item" in response  # If the item exists, it was copied before


def mark_image_as_copied(file_key: str, dry_run: bool):
    """Mark an image as copied in DynamoDB unless dry-run is enabled."""
    if dry_run:
        logger.info(f"🛑 Dry-Run: Would mark {file_key} as copied in DynamoDB.")
        return

    table = dynamodb.Table(TRACKING_TABLE)
    table.put_item(
        Item={"FileKey": file_key, "CopiedAt": datetime.utcnow().isoformat()}
    )


def update_image_count(job_id: str, count: int, dry_run: bool):
    """Update image count for a specific job in DynamoDB unless dry-run is enabled."""
    if dry_run:
        logger.info(f"🛑 Dry-Run: Would update image count for {job_id} by {count}.")
        return 0

    table = dynamodb.Table(DYNAMODB_TABLE)

    response = table.update_item(
        Key={"JobID": job_id},
        UpdateExpression="SET ImageCount = if_not_exists(ImageCount, :start) + :count, LastUpdated = :time",
        ExpressionAttributeValues={
            ":start": 0,
            ":count": count,
            ":time": datetime.utcnow().isoformat(),
        },
        ReturnValues="UPDATED_NEW",
    )

    new_count = response["Attributes"]["ImageCount"]
    logger.info(f"📊 Updated image count for {job_id}: {new_count}")
    return new_count


def check_and_trigger_ec2(image_count: int):
    """Trigger an EC2 instance if image count exceeds the threshold."""
    if image_count >= IMAGE_THRESHOLD:
        if not EC2_INSTANCE_ID:
            logger.error("❌ EC2_INSTANCE_ID is not set. Cannot trigger EC2.")
            return

        logger.info(
            f"🚀 Image count ({image_count}) exceeded threshold ({IMAGE_THRESHOLD}). Triggering EC2 instance {EC2_INSTANCE_ID}..."
        )
        response = ec2_client.start_instances(InstanceIds=[EC2_INSTANCE_ID])
        logger.info(f"✅ EC2 instance triggered: {response}")
    else:
        logger.info(
            f"🟢 Image count {image_count}/{IMAGE_THRESHOLD}. No EC2 trigger needed."
        )


def lambda_handler(event, context):
    """Process images and only copy non-duplicate ones."""
    try:
        # **Extract parameters from event payload**
        dry_run = event.get("dry_run", False)
        max_files = int(
            event.get("max_files", 100)
        )  # Default max to 100 if not provided
        prefixes = event.get("prefixes")  # Expecting a list of folder prefixes
        job_id = CURRENT_JOB_ID  # Use today's date as JobID
        total_copied = 0  # Track new images copied for today

        # **Ensure prefixes are provided**
        if not prefixes or not isinstance(prefixes, list) or len(prefixes) == 0:
            logger.error("❌ Error: No prefixes provided. Cannot proceed.")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    "Error: No prefixes provided. Please specify folders to process."
                ),
            }

        logger.info(f"📂 Processing {len(prefixes)} prefix(es): {prefixes}")

        # **Process each prefix separately**
        for prefix in prefixes:
            logger.info(f"🔎 Listing S3 objects from {CLIENT_BUCKET} (Prefix: {prefix})")
            response = s3_client.list_objects_v2(
                Bucket=CLIENT_BUCKET, Prefix=f"WEBDATA/{prefix}/"
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
                dest_key = f"{DEST_FOLDER}{os.path.basename(file_key)}"  # Store in images/yyyy-mm-dd/

                # **Check if the image was already copied**
                if image_already_copied(dest_key):
                    logger.info(f"🔁 Skipping {file_key}, already copied.")
                    continue  # Skip duplicate image

                # **Copy Image (Only if NOT Dry-Run)**
                if not dry_run:
                    copy_source = {"Bucket": CLIENT_BUCKET, "Key": file_key}
                    logger.info(f"📤 Copying {file_key} → {DEST_BUCKET}/{dest_key}")
                    s3_client.copy_object(
                        Bucket=DEST_BUCKET, Key=dest_key, CopySource=copy_source
                    )

                total_copied += 1

                # **Mark Image as Copied (Only if NOT Dry-Run)**
                mark_image_as_copied(dest_key, dry_run)

        # **Update Image Count (Only if NOT Dry-Run)**
        if total_copied > 0:
            new_count = update_image_count(job_id, total_copied, dry_run)
            check_and_trigger_ec2(new_count)

        logger.info(f"✅ Job {job_id} completed successfully (Dry-Run: {dry_run}).")
        return {
            "statusCode": 200,
            "body": json.dumps(f"Job {job_id} completed successfully."),
        }

    except Exception as e:
        logger.error(f"❌ Error during job processing: {str(e)}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps(f"Error: {str(e)}")}
