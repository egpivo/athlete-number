#!/bin/bash
#
# Updated Sync Script with Real-time PostgreSQL Integration
#

# Default parameters
SOURCE_BUCKET="s3://pc8tw.public/WEBDATA"
DEST_BUCKET="s3://athlete-number-detection/images"
DATE=$(date +%Y-%m-%d)  # Default to today's date
REGION="us-east-1"
MAX_PARALLEL_JOBS=6
EVENT_IDS=()

source $(poetry env info --path)/bin/activate

# Help function
usage() {
    echo "Usage: $0 [-d DATE] [-r REGION] [-j MAX_PARALLEL_JOBS] -e EVENT_ID1 EVENT_ID2 ..."
    exit 1
}

# Parse command-line arguments
while getopts "d:r:j:e:h" opt; do
    case ${opt} in
        d) DATE=$OPTARG ;;
        r) REGION=$OPTARG ;;
        j) MAX_PARALLEL_JOBS=$OPTARG ;;
        e) shift $((OPTIND - 1)); EVENT_IDS=("$@"); break ;;
        h) usage ;;
        *) usage ;;
    esac
done

# Validate event IDs
if [ ${#EVENT_IDS[@]} -eq 0 ]; then
    echo "Error: Provide at least one event ID with -e."
    usage
fi

# Create logs directory
mkdir -p logs

# Start Python script to process logs in real-time
python3 process_s3_log_live.py logs &

# Function to sync S3
sync_s3() {
    local EID_CID=$1
    echo "Syncing ${EID_CID}..."
    aws s3 sync "${SOURCE_BUCKET}/${EID_CID}/" "${DEST_BUCKET}/${DATE}/${EID_CID}" \
        --delete --region "${REGION}" | tee -a "logs/${EID_CID}.log" &
}

# Run jobs in parallel
SEMAPHORE="sync_semaphore"
mkfifo ${SEMAPHORE}
exec 3<>${SEMAPHORE}
rm ${SEMAPHORE}

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
