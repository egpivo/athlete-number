#!/bin/bash

# Default values
DRY_RUN=false
MAX_FILES=50
PREFIXES=""

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true ;;
        --max-files) MAX_FILES="$2"; shift ;;
        --prefixes) PREFIXES="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Lambda function name
LAMBDA_FUNCTION="athlete_number_detection_s3_ingestion_event"

# Convert comma-separated prefixes into JSON array format
IFS=',' read -r -a PREFIX_ARRAY <<< "$PREFIXES"
PREFIX_JSON_ARRAY=$(printf '"%s",' "${PREFIX_ARRAY[@]}")
PREFIX_JSON_ARRAY="[${PREFIX_JSON_ARRAY%,}]" # Remove the trailing comma

# Prepare JSON payload manually
PAYLOAD="{\"prefixes\": $PREFIX_JSON_ARRAY, \"dry_run\": $DRY_RUN, \"max_files\": $MAX_FILES}"

echo "🚀 Invoking Lambda function: $LAMBDA_FUNCTION"
echo "🔹 Dry-Run: $DRY_RUN"
echo "🔹 Max Files: $MAX_FILES"
echo "🔹 Prefixes: $PREFIX_JSON_ARRAY"
echo "🔹 Payload: $PAYLOAD"

aws lambda invoke --function-name "$LAMBDA_FUNCTION" \
    --payload "$PAYLOAD" \
    --cli-binary-format raw-in-base64-out response.json

echo "✅ Lambda execution complete. Check 'response.json' for details."
