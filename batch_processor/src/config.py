import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS S3 Configurations
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
DEST_BUCKET = os.getenv("DEST_BUCKET", "s3://athlete-number-detection")
DEST_FOLDER = os.getenv("DEST_FOLDER", "images")

# Processing settings
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 10))
MAX_IMAGES = int(os.getenv("MAX_IMAGES", 50))
OUTPUT_CSV = os.getenv("OUTPUT_CSV", "detection_results.csv")


DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PW")
DB_PORT = int(os.getenv("DB_PORT", 5432))


DB_CREDENTIALS = {
    "host": DB_HOST,
    "database": DB_NAME,
    "user": DB_USER,
    "password": DB_PASS,
    "port": DB_PORT,
}
