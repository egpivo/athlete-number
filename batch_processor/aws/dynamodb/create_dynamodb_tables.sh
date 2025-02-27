#!/bin/bash

# Set AWS region
AWS_REGION="us-east-1"
DDL_PATH=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ddl  # Ensure we point to the correct directory

# Function to create a table from a DDL file
create_table() {
    local ddl_file="$1"
    local table_name
    table_name=$(jq -r '.TableName' "$ddl_file")

    if [[ -z "$table_name" || "$table_name" == "null" ]]; then
        echo "❌ Error: Could not extract table name from $ddl_file. Skipping..."
        return
    fi

    echo "🚀 Creating DynamoDB table: $table_name using $ddl_file..."
    aws dynamodb create-table --cli-input-json file://"$ddl_file" --region "$AWS_REGION" --no-cli-pager

    echo "⏳ Waiting for '$table_name' to become ACTIVE..."
    aws dynamodb wait table-exists --table-name "$table_name" --region "$AWS_REGION" --no-cli-pager
    echo "✅ Table '$table_name' created successfully."
}

# Ensure the directory exists
if [[ ! -d "$DDL_PATH" ]]; then
    echo "❌ Error: Directory '$DDL_PATH' does not exist!"
    exit 1
fi

# Loop through all DDL files in the ddl/ directory
for ddl in "$DDL_PATH"/*.ddl; do
    if [[ -f "$ddl" ]]; then
        create_table "$ddl"
    else
        echo "⚠️ No DDL files found in '$DDL_PATH'."
    fi
done

echo "✅ All required DynamoDB tables have been created!"
