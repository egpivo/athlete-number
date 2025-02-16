#!/bin/bash

# Ensure default AWS credentials are used
export AWS_CONFIG_FILE=~/.aws/config
export AWS_SHARED_CREDENTIALS_FILE=~/.aws/credentials

# Define your S3 bucket
DEST_BUCKET="s3://athlete-number"
DEST_FOLDER="webdata-taipei-2025-02/images"

# List of source S3 paths
SRC_PATHS=(
    "s3://pc8tw.public/WEBDATA/778592_3175/"
    "s3://pc8tw.public/WEBDATA/778592_5881/"
    "s3://pc8tw.public/WEBDATA/778592_3551/"
    "s3://pc8tw.public/WEBDATA/778592_6252/"
)

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null
then
    echo "Error: AWS CLI is not installed. Please install AWS CLI and try again."
    exit 1
fi

# Loop through source paths and copy them
for SRC_PATH in "${SRC_PATHS[@]}"; do
    echo "Copying from $SRC_PATH to $DEST_BUCKET/$DEST_FOLDER..."

    # Perform S3 copy and check if the command is successful
    if aws s3 cp --recursive --exclude '*' --include '*_tn_*' "$SRC_PATH" "$DEST_BUCKET/$DEST_FOLDER/" --region us-east-1; then
        echo "Successfully copied from $SRC_PATH."
    else
        echo "Error: Failed to copy from $SRC_PATH." >&2
    fi
done

echo "S3 transfer complete."
