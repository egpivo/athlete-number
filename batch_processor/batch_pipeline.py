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
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 10))  # Default batch size is 10

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
    print(f"Downloading: {key}")
    bucket_name = bucket.replace("s3://", "")
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return BytesIO(response["Body"].read()), key  # Return image content + filename
    except Exception as e:
        print(f"Error downloading {key}: {e}")
        return None, key


def send_images_to_api(images):
    """Send batch images to the API for processing and return detected bib numbers."""
    files = [("files", (name, img.getvalue(), "image/jpeg")) for img, name in images]

    print(f"Sending {len(files)} images to API...")

    try:
        response = requests.post(
            API_URL, files=files, timeout=30
        )  # Add timeout for stability
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print("API request timed out!")
        return []
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return []


def save_results_to_csv(results, output_file="detection_results.csv"):
    """Append detection results to a CSV file."""
    df = pd.DataFrame(results)

    # Append without overwriting
    df.to_csv(
        output_file, mode="a", index=False, header=not os.path.exists(output_file)
    )

    print(f"Results saved to {output_file}")


def main():
    """Process images in batches."""
    print("Fetching images from S3...")
    image_keys = list_s3_images(DEST_BUCKET, DEST_FOLDER)

    if not image_keys:
        print("No images found in S3 bucket.")
        return

    print(f"Found {len(image_keys)} images. Processing in batches of {BATCH_SIZE}...")

    # Process in batches
    for i in range(0, len(image_keys), BATCH_SIZE):
        batch_keys = image_keys[i : i + BATCH_SIZE]  # Get a batch

        print(f"\nProcessing batch {i // BATCH_SIZE + 1}...")

        # Step 1: Download images
        images = [download_image(DEST_BUCKET, key) for key in batch_keys]
        images = [
            img for img in images if img[0] is not None
        ]  # Remove failed downloads

        if not images:
            print("Skipping batch due to failed downloads.")
            continue

        # Step 2: Process API
        detection_results = send_images_to_api(images)

        # Step 3: Save results
        save_results_to_csv(detection_results)

    print("\n✅ Processing complete!")


if __name__ == "__main__":
    main()
