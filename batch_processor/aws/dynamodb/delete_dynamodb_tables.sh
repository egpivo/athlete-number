#!/bin/bash

# Set AWS region
AWS_REGION="us-east-1"

# List of tables to delete
TABLES_TO_DELETE=(
    "athlete_number_detection_image_ingestion_tracker"
    "athlete_number_detection_image_tracker"
    "athlete_number_detection_job_counter"
)

# Function to delete a table
delete_table() {
    local table_name="$1"
    echo "🚨 Deleting table: $table_name..."
    aws dynamodb delete-table --table-name "$table_name" --region "$AWS_REGION"

    echo "⏳ Waiting for '$table_name' to be deleted..."
    aws dynamodb wait table-not-exists --table-name "$table_name" --region "$AWS_REGION"
    echo "✅ Table '$table_name' deleted successfully."
}

# Delete all tables
for table in "${TABLES_TO_DELETE[@]}"; do
    delete_table "$table"
done

echo "✅ All old DynamoDB tables have been deleted!"
