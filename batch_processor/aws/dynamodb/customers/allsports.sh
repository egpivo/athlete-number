#!/bin/bash

# Set AWS region
AWS_REGION="us-east-1"

# Define table names
CUSTOMER_TABLE="athlete_number_detection_customers"
USAGE_TABLE="athlete_number_detection_customer_usage"

# Customer details
CUSTOMER_ID="allsports"
CUSTOMER_NAME="創星影像股份有限公司"
CONTACT_EMAIL="allsports@photocreate.com.tw"
CONTACT_PHONE="886-2-7713-7190"
ADDRESS="10491台北市中山區建國北路二段147號13樓"
STATUS="active"
CREATED_AT=$(date -u +"%Y-%m-%d")

# Contract details
TOTAL_IMAGES_PROCESSED=0
CONTRACT_LIMIT=100000000  # 100M images
START_DATE="2025-03-01"
END_DATE="2025-10-31"

# Function to check if a customer exists
check_customer_exists() {
    aws dynamodb get-item \
        --table-name "$CUSTOMER_TABLE" \
        --key "{\"customer_id\": {\"S\": \"$CUSTOMER_ID\"}}" \
        --region "$AWS_REGION" \
        --query "Item.customer_id" \
        --output text 2>/dev/null
}

# Function to check if a customer usage record exists
check_usage_exists() {
    aws dynamodb get-item \
        --table-name "$USAGE_TABLE" \
        --key "{\"customer_id\": {\"S\": \"$CUSTOMER_ID\"}}" \
        --region "$AWS_REGION" \
        --query "Item.customer_id" \
        --output text 2>/dev/null
}

# Create customer if not exists
if [[ "$(check_customer_exists)" == "None" ]]; then
    echo "🚀 Adding customer: $CUSTOMER_NAME..."
    aws dynamodb put-item --table-name "$CUSTOMER_TABLE" --item "{
        \"customer_id\": {\"S\": \"$CUSTOMER_ID\"},
        \"customer_name\": {\"S\": \"$CUSTOMER_NAME\"},
        \"contact_email\": {\"S\": \"$CONTACT_EMAIL\"},
        \"contact_phone\": {\"S\": \"$CONTACT_PHONE\"},
        \"address\": {\"S\": \"$ADDRESS\"},
        \"created_at\": {\"S\": \"$CREATED_AT\"},
        \"status\": {\"S\": \"$STATUS\"}
    }" --region "$AWS_REGION"
    echo "✅ Customer added: $CUSTOMER_NAME"
else
    echo "✅ Customer '$CUSTOMER_NAME' already exists. Skipping creation."
fi

# Create customer usage record if not exists
if [[ "$(check_usage_exists)" == "None" ]]; then
    echo "🚀 Adding usage tracking for customer: $CUSTOMER_NAME..."
    aws dynamodb put-item --table-name "$USAGE_TABLE" --item "{
        \"customer_id\": {\"S\": \"$CUSTOMER_ID\"},
        \"total_images_processed\": {\"N\": \"$TOTAL_IMAGES_PROCESSED\"},
        \"contract_limit\": {\"N\": \"$CONTRACT_LIMIT\"},
        \"start_date\": {\"S\": \"$START_DATE\"},
        \"end_date\": {\"S\": \"$END_DATE\"}
    }" --region "$AWS_REGION"
    echo "✅ Usage tracking added for: $CUSTOMER_NAME"
else
    echo "✅ Usage tracking for '$CUSTOMER_NAME' already exists. Skipping creation."
fi

echo "🎯 All operations completed for customer: $CUSTOMER_NAME"
