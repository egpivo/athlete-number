#!/bin/bash

# Set AWS region
AWS_REGION="us-east-1"

# Define table names
IMAGE_TRACKER_TABLE="athlete_number_detection_image_tracker"
JOB_COUNTER_TABLE="athlete_number_detection_job_counter"

# Function to check if a table exists
check_table_exists() {
    local table_name="$1"
    aws dynamodb describe-table --table-name "$table_name" --region "$AWS_REGION" &>/dev/null
    return $?  # Return success (0) if table exists, error (1) if not
}

# Function to create a table if it does not exist
create_table() {
    local table_name="$1"
    local attribute_definitions="$2"
    local key_schema="$3"

    echo "🚀 Creating DynamoDB table: $table_name..."

    aws dynamodb create-table \
        --table-name "$table_name" \
        --attribute-definitions $attribute_definitions \
        --key-schema $key_schema \
        --billing-mode PAY_PER_REQUEST \
        --region "$AWS_REGION"

    echo "⏳ Waiting for table '$table_name' to become ACTIVE..."
    aws dynamodb wait table-exists --table-name "$table_name" --region "$AWS_REGION"
    echo "✅ DynamoDB table '$table_name' is now ACTIVE."
}

# Create IMAGE_TRACKER_TABLE (Prevents duplicate image processing)
if check_table_exists "$IMAGE_TRACKER_TABLE"; then
    echo "✅ DynamoDB table '$IMAGE_TRACKER_TABLE' already exists. Skipping creation."
else
    create_table "$IMAGE_TRACKER_TABLE" "AttributeName=FileKey,AttributeType=S" "AttributeName=FileKey,KeyType=HASH"
fi

# Create JOB_COUNTER_TABLE (Tracks total images per job)
if check_table_exists "$JOB_COUNTER_TABLE"; then
    echo "✅ DynamoDB table '$JOB_COUNTER_TABLE' already exists. Skipping creation."
else
    create_table "$JOB_COUNTER_TABLE" "AttributeName=JobID,AttributeType=S" "AttributeName=JobID,KeyType=HASH"
fi

# Verify table statuses
echo "🔍 Verifying table statuses..."
aws dynamodb describe-table --table-name "$IMAGE_TRACKER_TABLE" --region "$AWS_REGION" | grep '"TableStatus":'
aws dynamodb describe-table --table-name "$JOB_COUNTER_TABLE" --region "$AWS_REGION" | grep '"TableStatus":'

echo "✅ All required DynamoDB tables are ready!"
