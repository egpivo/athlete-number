import argparse
import os
from io import BytesIO

import boto3
import pandas as pd
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Batch process images from S3")
parser.add_argument(
    "--max_images", type=int, default=50, help="Maximum number of images to process"
)
parser.add_argument(
    "--batch_size", type=int, default=10, help="Number of images to process per batch"
)
args = parser.parse_args()

# AWS S3 Configurations
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
DEST_BUCKET = os.getenv("DEST_BUCKET", "s3://athlete-number")
DEST_FOLDER = os.getenv("DEST_FOLDER", "webdata-taipei-2025-02/images")
BATCH_SIZE = args.batch_size
MAX_IMAGES = args.max_images

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
    all_images = [
        obj["Key"]
        for obj in response.get("Contents", [])
        if obj["Key"].endswith((".jpg", ".jpeg", ".png"))
    ]
    return all_images[:MAX_IMAGES]


def download_image(bucket, key):
    """Download an image from S3 and return it as a file-like object."""
    print(f"Downloading: {key}")
    bucket_name = bucket.replace("s3://", "")
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return BytesIO(response["Body"].read()), key
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


def process_results(results, processed_files):
    """Convert API response to structured format for CSV saving.
    Ensures every processed file is recorded, even if no numbers are detected.
    """
    rows = []
    detected_files = {
        result["filename"].split("/")[-1].split("_tn_")[0] for result in results
    }

    for result in results:
        filename = result["filename"].split("/")[-1].split("_tn_")[0]
        if result["athlete_numbers"]:
            for tag in result["athlete_numbers"]:
                rows.append([filename, tag])
        else:
            rows.append([filename, None])

    # Ensure all processed files are included, even if API didn't return them
    for filename in processed_files:
        clean_filename = filename.split("/")[-1].split("_tn_")[0]
        if clean_filename not in detected_files:
            rows.append([clean_filename, None])

    return rows


def save_results_to_csv(results, processed_files, output_file="detection_results.csv"):
    """Append detection results to a CSV file, ensuring all processed files are recorded."""
    structured_results = process_results(results, processed_files)
    df = pd.DataFrame(structured_results, columns=["photonum", "tag"])

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

    print(
        f"Found {len(image_keys)} images (max {MAX_IMAGES}). Processing in batches of {BATCH_SIZE}..."
    )

    # Process in batches
    for i in range(0, len(image_keys), BATCH_SIZE):
        batch_keys = image_keys[i : i + BATCH_SIZE]

        print(f"\nProcessing batch {i // BATCH_SIZE + 1}...")
        images = [download_image(DEST_BUCKET, key) for key in batch_keys]
        images = [img for img in images if img[0] is not None]

        if not images:
            print("Skipping batch due to failed downloads.")
            continue

        detection_results = send_images_to_api(images)
        save_results_to_csv(detection_results, batch_keys)

    print("\n✅ Processing complete!")


if __name__ == "__main__":
    main()
