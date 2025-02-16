import os
from io import BytesIO

import boto3
import pandas as pd
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS S3 Configurations
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
DEST_BUCKET = os.getenv("DEST_BUCKET", "s3://athlete-number")
DEST_FOLDER = os.getenv("DEST_FOLDER", "webdata-taipei-2025-02/images")

# API Configurations
API_URL = os.getenv("BACKEND_URL", "http://localhost:5566") + "/extract/bib-numbers"

# Initialize S3 Client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
)


def list_s3_images(bucket, prefix):
    """List image files in the given S3 folder."""
    bucket_name = bucket.replace("s3://", "")
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    return [
        obj["Key"]
        for obj in response.get("Contents", [])
        if obj["Key"].endswith((".jpg", ".jpeg", ".png"))
    ]


def download_image(bucket, key):
    """Download an image from S3 and return it as a file-like object."""
    bucket_name = bucket.replace("s3://", "")
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    return BytesIO(response["Body"].read())


def send_images_to_api(images):
    """Send batch images to the API for processing and return detected bib numbers."""
    files = [("files", (name, img.getvalue(), "image/jpeg")) for name, img in images]
    response = requests.post(API_URL, files=files)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return []


def save_results_to_csv(results, output_file="detection_results.csv"):
    """Save detection results to a CSV file."""
    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False)
    print(f"Results saved to {output_file}")


def main():
    """Main processing pipeline."""
    print("Fetching images from S3...")
    image_keys = list_s3_images(DEST_BUCKET, DEST_FOLDER)

    if not image_keys:
        print("No images found in S3 bucket.")
        return

    print(f"Found {len(image_keys)} images. Downloading and processing...")

    # Download images from S3
    images = [(key, download_image(DEST_BUCKET, key)) for key in image_keys]

    # Send images to API
    print("Sending images to API...")
    detection_results = send_images_to_api(images)

    # Save results to CSV
    save_results_to_csv(detection_results)


if __name__ == "__main__":
    main()
