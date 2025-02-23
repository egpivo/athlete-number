#!/bin/bash

# Usage:
# ./run_lambda_ingestion.sh --dry-run --max-files 100
# ./run_lambda_ingestion.sh --max-files 500
# ./run_lambda_ingestion.sh  (default: no dry-run, 50 max files)

# Default values
DRY_RUN=false
MAX_FILES=50

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true ;;
        --max-files) MAX_FILES="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Lambda function name
LAMBDA_FUNCTION="athlete_number_detection_s3_ingestion_event"

# Prepare payload
PAYLOAD=$(jq -n --argjson dry_run "$DRY_RUN" --argjson max_files "$MAX_FILES" '{"dry_run": $dry_run, "max_files": $max_files}')

echo "🚀 Invoking Lambda ($LAMBDA_FUNCTION) with dry-run = $DRY_RUN, max-files = $MAX_FILES..."

aws lambda invoke --function-name "$LAMBDA_FUNCTION" \
    --payload "$PAYLOAD" \
    --cli-binary-format raw-in-base64-out response.json

echo "✅ Lambda execution complete. Check response.json for details."
