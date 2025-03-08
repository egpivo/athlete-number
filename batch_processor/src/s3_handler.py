import asyncio
import logging
import os

import aiobotocore
import boto3
import cv2
import numpy as np
from botocore.config import Config
from src.config import AWS_ACCESS_KEY, AWS_SECRET_KEY, DEST_BUCKET

logger = logging.getLogger(__name__)

# Initialize S3 client
boto_config = Config(max_pool_connections=200)
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    config=boto_config,
)


async def list_s3_images_incremental(
    bucket, prefix, last_processed_key=None, batch_size=1000
):
    """Async generator that streams images in batches (Fix for 'async for' error)."""
    paginator = s3_client.get_paginator("list_objects_v2")
    pagination_config = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": batch_size}

    if last_processed_key:
        pagination_config["StartAfter"] = last_processed_key

    try:
        page_iterator = paginator.paginate(**pagination_config)

        for page in page_iterator:
            await asyncio.sleep(0)  # ✅ Allows async event loop to continue

            if "Contents" not in page:
                break  # No more files

            batch_files = sorted(
                (
                    {"Key": obj["Key"], "LastModified": obj["LastModified"]}
                    for obj in page["Contents"]
                    if obj["Key"].lower().endswith((".jpg", ".jpeg", ".png"))
                ),
                key=lambda x: x["LastModified"],
                reverse=True,
            )

            next_start_after = batch_files[-1]["Key"] if batch_files else None
            yield [
                img["Key"] for img in batch_files
            ], next_start_after  # ✅ Now async generator

    except Exception as e:
        logger.error(f"❌ Error listing S3 objects: {e}")
        yield [], None


def list_s3_images(bucket: str, prefix: str, max_images: int) -> list:
    """List image files from S3."""
    bucket_name = bucket.replace("s3://", "")
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    all_images = [
        obj["Key"]
        for obj in response.get("Contents", [])
        if obj["Key"].endswith((".jpg", ".jpeg", ".png"))
    ]
    return all_images[:max_images]


async def download_image(bucket: str, key: str):
    """Download an image from S3 and return a PIL Image object."""
    print(f"Downloading: {key}")
    bucket_name = bucket.replace("s3://", "")

    try:
        response = await asyncio.to_thread(
            s3_client.get_object, Bucket=bucket_name, Key=key
        )
        image_bytes = response["Body"].read()
        image_np = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

        if image is None:
            logger.warning(f"Failed to decode image {key}. Skipping.")
            return None, key

        return image, key
    except Exception as e:
        logger.error(f"Error downloading {key}: {e}")
        return None, key


async def batch_download_images(image_keys: list, local_dir: str):
    """Download images maintaining original directory structure."""
    os.makedirs(local_dir, exist_ok=True)

    async def download_single(key):
        img_bytes, _ = await download_image(DEST_BUCKET, key)
        if img_bytes is not None:
            local_path = os.path.join(local_dir, key)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(img_bytes)
            return key, local_path
        return None

    results = await asyncio.gather(*(download_single(k) for k in image_keys))
    return [(key, path) for key, path in results if path is not None]


async def read_checkpoint(bucket: str, key: str) -> str:
    """Asynchronously reads the last processed image key from S3."""
    session = aiobotocore.get_session()
    async with session.create_client("s3") as s3_client:
        try:
            response = await s3_client.get_object(
                Bucket=bucket.replace("s3://", ""), Key=key
            )
            checkpoint = await response["Body"].read()
            checkpoint_value = checkpoint.decode("utf-8").strip()
            logger.info(f"📌 Last checkpoint read: {checkpoint_value}")
            return checkpoint_value
        except s3_client.exceptions.NoSuchKey:
            logger.info("🛑 No checkpoint found. Starting from the beginning.")
            return None
        except Exception as e:
            logger.error(f"❌ Error reading checkpoint: {e}")
            return None


async def write_checkpoint(bucket: str, key: str, checkpoint_value: str) -> None:
    """Asynchronously writes the last processed image key to S3."""
    session = aiobotocore.get_session()
    async with session.create_client("s3") as s3_client:
        try:
            await s3_client.put_object(
                Bucket=bucket.replace("s3://", ""),
                Key=key,
                Body=checkpoint_value.encode("utf-8"),
            )
            logger.info(f"✅ Checkpoint updated: {checkpoint_value}")
        except Exception as e:
            logger.error(f"❌ Error writing checkpoint: {e}")
