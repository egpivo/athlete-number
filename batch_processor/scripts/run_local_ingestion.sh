#!/bin/bash
#
# Example: ./run_local_ingestion.sh -d test -i 778592_3169 -i 778592_3456 -n
#

# Define your S3 bucket
DEST_BUCKET="s3://athlete-number-detection"
NEW_FOLDER=""
IDS=()
DRY_RUN=false

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null
then
    echo "Error: AWS CLI is not installed. Please install AWS CLI and try again."
    exit 1
fi

# Function to display usage
usage() {
    echo "Usage: $0 -d <new_folder> -i <id1> -i <id2> ... [-n]"
    exit 1
}

# Parse command-line arguments
while getopts ":d:i:n" opt; do
    case ${opt} in
        d ) NEW_FOLDER="$OPTARG" ;;
        i ) IDS+=("$OPTARG") ;;
        n ) DRY_RUN=true ;;
        \? ) echo "Invalid option: -$OPTARG" >&2; usage ;;
        : ) echo "Option -$OPTARG requires an argument." >&2; usage ;;
    esac
done

# Validate inputs
if [[ -z "$NEW_FOLDER" || ${#IDS[@]} -eq 0 ]]; then
    usage
fi

# Set AWS credentials
export AWS_CONFIG_FILE=./.client_aws/config
export AWS_SHARED_CREDENTIALS_FILE=./.client_aws/credentials
export AWS_PROFILE=devInstAI  # Ensure the correct profile is used

# Verify AWS credentials
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity &>/dev/null; then
    echo "Error: Unable to authenticate with AWS. Check your credentials."
    exit 1
fi
echo "AWS authentication successful."

# Loop through provided IDs and copy them
for ID in "${IDS[@]}"; do
    SRC_PATH="s3://pc8tw.public/WEBDATA/$ID/"
    DEST_PATH="$DEST_BUCKET/images/$NEW_FOLDER/"

    echo "Copying from $SRC_PATH to $DEST_PATH..."

    if [ "$DRY_RUN" = true ]; then
        # Fetch the first file (without filtering)
        FIRST_FILE=$(aws s3api list-objects-v2 --bucket pc8tw.public --prefix "WEBDATA/$ID/" \
            --max-items 1 --query "Contents[0].Key" --output text 2>/dev/null | head -n 1)

        if [[ -n "$FIRST_FILE" && "$FIRST_FILE" != "None" && "$FIRST_FILE" != "null" ]]; then
            BASENAME=$(basename "$FIRST_FILE")
            echo "(dryrun) copy: s3://pc8tw.public/$FIRST_FILE to $DEST_PATH$BASENAME"
        else
            echo "Warning: No files found in $SRC_PATH."
        fi
    else
        # Perform full S3 copy
        if aws s3 cp --recursive "$SRC_PATH" "$DEST_PATH" --region us-east-1; then
            echo "Successfully copied from $SRC_PATH to $DEST_PATH."
        else
            echo "Error: Failed to copy from $SRC_PATH." >&2
        fi
    fi
done

echo "S3 transfer complete."
