import logging

import boto3
from src.config import CLIENT_BUCKET

logger = logging.getLogger()
s3_client = boto3.client("s3")


def list_sorted_s3_objects(bucket_name, prefix, offset, batch_size):
    """List S3 objects sorted by LastModified timestamp using offset and batch processing"""
    all_files = []
    seen_keys = set()  # Track unique file keys to prevent duplicates

    paginator = s3_client.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    for page in page_iterator:
        if "Contents" not in page:
            print(f"❌ No files found in prefix: {prefix}")
            continue

        for obj in page["Contents"]:
            if obj["Key"] not in seen_keys:  # Avoid duplicates
                seen_keys.add(obj["Key"])
                all_files.append(
                    {"Key": obj["Key"], "LastModified": obj["LastModified"]}
                )

    print(f"🔍 Found {len(all_files)} unique files before sorting for prefix '{prefix}'")

    if not all_files:
        return []

    # Sort by LastModified (most recent first)
    all_files.sort(key=lambda x: x["LastModified"], reverse=True)

    # Apply offset & batch selection
    start_index = offset * batch_size
    end_index = start_index + batch_size

    selected_files = all_files[start_index:end_index]
    print(f"✅ Returning {len(selected_files)} files from {start_index} to {end_index}")

    return selected_files


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
