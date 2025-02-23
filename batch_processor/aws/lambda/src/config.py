import os
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS Config
CLIENT_BUCKET = os.getenv("CLIENT_BUCKET", "pc8tw.public")
DEST_BUCKET = os.getenv("DEST_BUCKET", "athlete-number-detection")
CUSTOMER_USAGE_TABLE = os.getenv(
    "CUSTOMER_USAGE_TABLE", "athlete_number_detection_customer_usage"
)
JOB_COUNTER_TABLE = "athlete_number_detection_job_counter"
IMAGE_TRACKER_TABLE = "athlete_number_detection_image_tracker"
INSTANCE_ID = os.getenv("INSTANCE_ID")
DEFAULT_CUSTOMER_ID = "allsports"

# Date Formatting
TODAY_DATE = datetime.utcnow().strftime("%Y-%m-%d")
DEST_FOLDER = f"images/{TODAY_DATE}/"

# Batch Size
BATCH_SIZE = 50

ENV_PREFIXES = os.getenv("PREFIXES", "").split(",")
ENV_PREFIXES = [p.strip() for p in ENV_PREFIXES if p.strip()]
