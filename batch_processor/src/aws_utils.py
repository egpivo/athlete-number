import logging
from datetime import datetime
from typing import Any, Dict, Optional

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# AWS Clients
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# Table Names
IMAGE_TRACKER_TABLE = "athlete_number_detection_image_tracker"
JOB_COUNTER_TABLE = "athlete_number_detection_job_counter"


def upload_to_s3(file_path: str, bucket: str, key: str) -> None:
    """Upload file to S3."""
    try:
        s3_client.upload_file(file_path, bucket, key)
        logger.info(f"✅ Uploaded {file_path} to s3://{bucket}/{key}")
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")


def query_dynamodb(table_name: str, key: str) -> Optional[Dict[str, Any]]:
    """Query DynamoDB for an item."""
    table = dynamodb.Table(table_name)
    response = table.get_item(Key={"FileKey": key})
    return response.get("Item")


def store_to_dynamodb(table_name: str, data: Dict[str, Any]) -> None:
    """Store an item in DynamoDB."""
    table = dynamodb.Table(table_name)
    table.put_item(Item=data)


def image_already_copied(file_key: str) -> bool:
    """Check if an image exists in DynamoDB."""
    table = dynamodb.Table(IMAGE_TRACKER_TABLE)
    response = table.get_item(Key={"FileKey": file_key})
    return "Item" in response


def mark_image_as_copied(file_key: str, dry_run: bool) -> None:
    """Mark an image as copied unless in dry-run mode."""
    if dry_run:
        logger.info(f"🛑 Dry-Run: Would mark {file_key} as copied.")
        return

    table = dynamodb.Table(IMAGE_TRACKER_TABLE)
    table.put_item(
        Item={"FileKey": file_key, "CopiedAt": datetime.utcnow().isoformat()}
    )


def update_image_count(job_id: str, count: int, dry_run: bool) -> int:
    """Update image count for a job."""
    if dry_run:
        logger.info(f"🛑 Dry-Run: Would update image count for {job_id} by {count}.")
        return 0

    table = dynamodb.Table(JOB_COUNTER_TABLE)

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
