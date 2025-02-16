import csv
import os
from io import BytesIO

import boto3
import requests
from dotenv import load_dotenv

# Load environment variables (optional)
load_dotenv()

# AWS S3 Configurations
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_PREFIX = os.getenv("S3_PREFIX", "")  # Optional folder path inside S3 bucket

# API Configurations
API_URL = os.getenv("BACKEND_URL", "http://localhost:5566") + "/extract/bib-numbers"

# CSV Output File
OUTPUT_CSV = "detection_results.csv"

# Initialize S3 Client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
)


def list_images_in_s3(bucket_name, prefix=""):
    """List image files in an S3 bucket."""
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    return [
        obj["Key"]
        for obj in response.get("Contents", [])
        if obj["Key"].endswith((".jpg", ".jpeg", ".png"))
    ]


def download_image_from_s3(bucket_name, key):
    """Download an image from S3 and return it as a file-like object."""
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


def save_results_to_csv(results, output_file):
    """Save detection results to a CSV file."""
    with open(output_file, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Filename", "Detected Bib Numbers"])  # Header

        for result in results:
            filename = result.get("filename", "Unknown")
            bib_numbers = ", ".join(
                map(str, result.get("athlete_numbers", ["Not detected"]))
            )
            writer.writerow([filename, bib_numbers])

    print(f"Results saved to {output_file}")


def main():
    """Main pipeline to process images from S3 and save results."""
    print("Fetching image list from S3...")
    image_keys = list_images_in_s3(S3_BUCKET_NAME, S3_PREFIX)

    if not image_keys:
        print("No images found in S3 bucket.")
        return

    print(f"Found {len(image_keys)} images. Downloading and processing...")

    # Download images from S3
    images = [(key, download_image_from_s3(S3_BUCKET_NAME, key)) for key in image_keys]

    # Send images to API for detection
    print("Sending images to API...")
    detection_results = send_images_to_api(images)
    save_results_to_csv(detection_results, OUTPUT_CSV)


if __name__ == "__main__":
    main()
