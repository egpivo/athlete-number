#!/bin/bash

# Configuration
AWS_REGION="us-east-1"
LAMBDA_FUNCTION_NAME="athlete_number_detection_s3_ingestion_event"
ZIP_FILE="aws/lambda/lambda_function.zip"

echo "🚀 Verifying AWS Lambda Deployment: $LAMBDA_FUNCTION_NAME"

# 1️⃣ Check the Last Modified Timestamp
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

# 2️⃣ Verify the Deployed Code SHA256 Hash
echo "🔍 Checking deployed code integrity..."
DEPLOYED_HASH=$(aws lambda get-function \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --region "$AWS_REGION" \
    --query 'Configuration.CodeSha256' \
    --output text)

if [ -f "$ZIP_FILE" ]; then
    LOCAL_HASH=$(openssl dgst -sha256 "$ZIP_FILE" | awk '{print $2}')
    if [ "$DEPLOYED_HASH" == "$LOCAL_HASH" ]; then
        echo "✅ Code hash matches: $DEPLOYED_HASH"
    else
        echo "⚠️ Warning: Hash mismatch! Deployed: $DEPLOYED_HASH, Local: $LOCAL_HASH"
    fi
else
    echo "⚠️ Warning: Local zip file '$ZIP_FILE' not found, skipping hash verification."
fi

# 3️⃣ Invoke the Lambda Function with a Test Payload
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

# 4️⃣ Retrieve and Display CloudWatch Logs
echo "📜 Fetching recent logs from AWS CloudWatch..."
aws logs tail "/aws/lambda/$LAMBDA_FUNCTION_NAME" --region "$AWS_REGION" --follow

echo "🚀 Verification complete!"
