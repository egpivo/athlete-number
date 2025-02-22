import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS S3 Configurations
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
DEST_BUCKET = os.getenv("DEST_BUCKET", "s3://athlete-number")
DEST_FOLDER = os.getenv("DEST_FOLDER", "webdata-taipei-2025-02/images")

# Processing settings
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 10))
MAX_IMAGES = int(os.getenv("MAX_IMAGES", 50))
OUTPUT_CSV = os.getenv("OUTPUT_CSV", "detection_results.csv")
