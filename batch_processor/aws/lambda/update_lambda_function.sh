#!/bin/bash

# Configuration
AWS_REGION="us-east-1"
LAMBDA_FUNCTION_NAME="athlete_number_detection_s3_ingestion_event"
LAMBDA_SRC_DIR="aws/lambda"
S3_BUCKET="athlete-number-detection"
S3_KEY="lambda_deployments/lambda_function.zip"
TMP_DIR="/tmp/lambda_package"
ZIP_FILE="lambda_function.zip"

# Ensure AWS CLI does not use a pager
export AWS_PAGER=""

# Check if AWS CLI is installed
if ! command -v aws &>/dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI first."
    exit 1
fi

# Clean up previous Lambda package
echo "🗑️ Cleaning up previous Lambda package..."
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

# Install dependencies in a separate directory
echo "📦 Installing dependencies into $TMP_DIR..."
pip install -r requirements.txt -t "$TMP_DIR" > /dev/null

# Copy only necessary Lambda files
echo "📂 Copying Lambda source files..."
rsync -av --exclude="*.pyc" --exclude="__pycache__" "$LAMBDA_SRC_DIR/" "$TMP_DIR/" > /dev/null

# Create a zip package **inside /tmp/lambda_package**
echo "📦 Creating deployment package..."
cd "$TMP_DIR" || exit 1
zip -r "$ZIP_FILE" . > /dev/null

# Ensure the ZIP file was created inside /tmp/lambda_package
if [ ! -f "$ZIP_FILE" ]; then
    echo "❌ Error: Deployment package '$ZIP_FILE' not found in $TMP_DIR!"
    exit 1
fi

# Move ZIP to the root project directory
mv "$ZIP_FILE" "$OLDPWD/"
cd - || exit 1

# Ensure the ZIP file exists before proceeding
if [ ! -f "$ZIP_FILE" ]; then
    echo "❌ Error: Deployment package '$ZIP_FILE' not found in root directory!"
    exit 1
fi

# Upload ZIP to S3
echo "🚀 Uploading deployment package to S3: s3://$S3_BUCKET/$S3_KEY"
if aws s3 cp "$ZIP_FILE" "s3://$S3_BUCKET/$S3_KEY" --region "$AWS_REGION"; then
    echo "✅ Upload successful!"
else
    echo "❌ Error uploading to S3!"
    exit 1
fi

# Update Lambda function from S3
echo "🚀 Updating Lambda function: $LAMBDA_FUNCTION_NAME from S3..."
if aws lambda update-function-code \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --s3-bucket "$S3_BUCKET" \
    --s3-key "$S3_KEY" \
    --region "$AWS_REGION"; then
    echo "✅ Lambda function updated successfully!"
else
    echo "❌ Error updating Lambda function from S3!"
    exit 1
fi

# Cleanup
rm "$ZIP_FILE"
rm -rf "$TMP_DIR"
echo "🗑️ Removed temporary files."
