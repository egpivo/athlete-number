#!/bin/bash
#
#
# Examples
#   - Provide Event IDs Only: ./sync_script.sh -d 2025-02-26 -e 778592_3169 778592_3456
#   - Customize Date: ./sync_script.sh -e 778592_3169 778592_3456 778592_3952
#
#

# Default parameters
SOURCE_BUCKET="s3://pc8tw.public/WEBDATA"
DEST_BUCKET="s3://athlete-number-detection/images"
DATE=$(date +%Y-%m-%d)  # Default to today's date
REGION="us-east-1"
MAX_PARALLEL_JOBS=6
EVENT_IDS=()

# Help function
usage() {
    echo "Usage: $0 [-d DATE] [-r REGION] [-j MAX_PARALLEL_JOBS] -e EVENT_ID1 EVENT_ID2 ..."
    echo ""
    echo "  -d DATE                 Specify a custom date (default: today's date)"
    echo "  -r REGION               Specify AWS region (default: us-east-1)"
    echo "  -j MAX_PARALLEL_JOBS    Specify the number of parallel jobs (default: 4)"
    echo "  -e EVENT_IDS            Space-separated list of event IDs (required)"
    echo "  -h                      Display this help message"
    exit 1
}

# Parse command-line arguments
while getopts "d:r:j:e:h" opt; do
    case ${opt} in
        d) DATE=$OPTARG ;;
        r) REGION=$OPTARG ;;
        j) MAX_PARALLEL_JOBS=$OPTARG ;;
        e) shift $((OPTIND - 1)); EVENT_IDS=("$@"); break ;;  # Capture remaining arguments as event IDs
        h) usage ;;
        *) usage ;;
    esac
done

# Validate that at least one event ID was provided
if [ ${#EVENT_IDS[@]} -eq 0 ]; then
    echo "Error: You must provide at least one event ID with the -e flag."
    usage
fi

# Create logs directory if not exists
mkdir -p logs

# Function to sync S3
sync_s3() {
    local EID_CID=$1
    echo "Syncing ${EID_CID}..."
    aws s3 sync "${SOURCE_BUCKET}/${EID_CID}/" "${DEST_BUCKET}/${DATE}/${EID_CID}" \
        --delete --region "${REGION}" >> "logs/${EID_CID}.log" 2>&1
}

# Run jobs in parallel with control
SEMAPHORE="sync_semaphore"
mkfifo ${SEMAPHORE}
exec 3<>${SEMAPHORE}
rm ${SEMAPHORE}

# Initialize the semaphore with empty slots
for ((i = 0; i < MAX_PARALLEL_JOBS; i++)); do echo; done >&3

for EID_CID in "${EVENT_IDS[@]}"; do
    read -u 3
    {
        sync_s3 "$EID_CID"
        echo >&3
    } &
done

wait
exec 3>&-  # Close file descriptor

echo "All sync operations completed."
