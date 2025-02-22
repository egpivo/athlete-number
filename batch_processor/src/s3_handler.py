import asyncio

import boto3
import cv2
import numpy as np
from PIL import Image
from src.config import AWS_ACCESS_KEY, AWS_SECRET_KEY, DEST_BUCKET

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
)


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
            print(f"Failed to decode image {key}. Skipping.")
            return None, key

        return Image.fromarray(image), key
    except Exception as e:
        print(f"Error downloading {key}: {e}")
        return None, key


async def batch_download_images(image_keys: list):
    """Download multiple images asynchronously."""
    tasks = [download_image(DEST_BUCKET, key) for key in image_keys]
    results = await asyncio.gather(*tasks)
    return [(img, key) for img, key in results if img is not None]
