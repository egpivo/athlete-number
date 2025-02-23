#!/bin/bash

# Configuration
AWS_REGION="us-east-1"
LAMBDA_FUNCTION_NAME="athlete_number_detection_s3_ingestion_event"
ZIP_FILE="aws/lambda/lambda_function.zip"

echo "🚀 Verifying AWS Lambda Deployment: $LAMBDA_FUNCTION_NAME"

# Check the Last Modified Timestamp
echo "📅 Fetching last modified timestamp..."
LAST_MODIFIED=$(aws lambda get-function-configuration \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --region "$AWS_REGION" \
    --query 'LastModified' \
    --output text)

if [ -z "$LAST_MODIFIED" ]; then
    echo "❌ Error: Could not retrieve last modified timestamp!"
    exit 1
else
    echo "✅ Last Modified: $LAST_MODIFIED"
fi

#  Invoke the Lambda Function with a Test Payload
echo "🛠️ Testing Lambda execution..."
TEST_PAYLOAD='{"dry_run": true, "max_files": 10}'
RESPONSE_FILE="response.json"

aws lambda invoke \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --payload "$TEST_PAYLOAD" \
    --cli-binary-format raw-in-base64-out \
    "$RESPONSE_FILE" \
    --region "$AWS_REGION" > /dev/null

if [ -s "$RESPONSE_FILE" ]; then
    echo "✅ Lambda invocation successful. Response:"
    cat "$RESPONSE_FILE"
else
    echo "❌ Error: Lambda invocation failed!"
fi

# Retrieve and Display CloudWatch Logs
echo "📜 Fetching recent logs from AWS CloudWatch..."
aws logs tail "/aws/lambda/$LAMBDA_FUNCTION_NAME" --region "$AWS_REGION" --follow

echo "🚀 Verification complete!"
