import json
import logging
import os

import boto3
from dotenv import load_dotenv
from lambda_function import lambda_handler  # Import your Lambda function

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Mock event for testing
test_event = {
    "dry_run": False,  # Set to False to actually process images
    "max_files": 100,  # Test with a small batch first
    "customer_id": "allsports",
    "prefixes": ["778592_3175", "778592_5881"],  # Adjust prefixes
}

# AWS Configuration (ensure valid credentials)
boto3.setup_default_session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

# Run the function locally
if __name__ == "__main__":
    print("🚀 Running Lambda locally...")
    response = lambda_handler(test_event, None)
    print("✅ Lambda Response:", json.dumps(response, indent=4))
