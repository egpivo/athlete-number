import logging

import boto3
from src.config import CLIENT_BUCKET

logger = logging.getLogger()
s3_client = boto3.client("s3")


def list_s3_images_incremental(
    bucket, prefix, last_processed_key=None, batch_size=1000
):
    """List S3 objects sorted by LastModified while supporting checkpoints."""
    paginator = s3_client.get_paginator("list_objects_v2")

    # Set up pagination configuration
    pagination_config = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": batch_size}

    if last_processed_key:
        pagination_config["StartAfter"] = last_processed_key

    try:
        page_iterator = paginator.paginate(**pagination_config)

        for page in page_iterator:
            if "Contents" not in page:
                return [], None  # No more files

            batch_files = [
                {"Key": obj["Key"], "LastModified": obj["LastModified"]}
                for obj in page["Contents"]
                if obj["Key"]
                .lower()
                .endswith((".jpg", ".jpeg", ".png"))  # Filter images only
            ]
            batch_files.sort(key=lambda x: x["LastModified"], reverse=True)

            # Get next start_after key
            next_start_after = batch_files[-1]["Key"] if batch_files else None

            return batch_files, next_start_after

    except Exception as e:
        print(f"❌ Error listing S3 objects: {e}")
        return [], None


def copy_s3_object(source_key, dest_bucket, dest_key):
    """Copy object from source S3 bucket to destination"""
    try:
        s3_client.copy_object(
            Bucket=dest_bucket,
            Key=dest_key,
            CopySource={"Bucket": CLIENT_BUCKET, "Key": source_key},
        )
        logger.info(f"✅ Copied {source_key} to {dest_key}")
    except Exception as e:
        logger.error(f"❌ Error copying file {source_key}: {str(e)}")
