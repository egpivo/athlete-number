#!/bin/bash
#
# Updated Sync Script with Real-time PostgreSQL Integration
# Example
# - ./run_aws_s3_sync.sh -d 2025-03-02 -n production 778759_3307 778759_6252 778759_5876
#

# Default parameters
SOURCE_BUCKET="s3://pc8tw.public/WEBDATA"
DEST_BUCKET="s3://athlete-number-detection/images"
DATE=$(date +%Y-%m-%d)  # Default to today's date
REGION="us-east-1"
MAX_PARALLEL_JOBS=6
EVENT_IDS=()
ENV="production"  # Default environment

# ✅ Activate Poetry Environment safely
POETRY_ENV_PATH=$(poetry env info --path 2>/dev/null)
if [ -d "$POETRY_ENV_PATH" ]; then
    source "$POETRY_ENV_PATH/bin/activate"
else
    echo "⚠️ Poetry environment not found! Ensure that 'poetry install' has been run."
    exit 1
fi

# ✅ Parse command-line arguments correctly
while getopts "d:r:j:n:h" opt; do
    case ${opt} in
        d) DATE=$OPTARG ;;    # Cutoff date
        r) REGION=$OPTARG ;;  # AWS region
        j) MAX_PARALLEL_JOBS=$OPTARG ;;  # Parallel jobs
        n) ENV=$OPTARG ;;  # Environment (test/prod)
        h) usage ;;
        *) usage ;;
    esac
done

# ✅ Shift remaining positional arguments into EVENT_IDS
shift $((OPTIND - 1))
EVENT_IDS=("$@")  # Capture all remaining args as event IDs

# ✅ Validate event IDs
if [ ${#EVENT_IDS[@]} -eq 0 ]; then
    echo "❌ Error: Provide at least one event ID."
    exit 1
fi

# ✅ Create logs directory
mkdir -p logs

echo "📅 Cutoff date set to: $DATE, 🏗️ Environment: $ENV"
echo "🎯 Event IDs to process: ${EVENT_IDS[*]}"

# ✅ Start Python script safely
python3 process_s3_log_live.py logs "$DATE" "$ENV" &
PYTHON_PID=$!
sleep 5

if ! kill -0 $PYTHON_PID 2>/dev/null; then
    echo "❌ Error: Python ingestion process failed to start!"
    exit 1
fi
echo "📡 Started process_s3_log_live.py with cutoff_date: $DATE and env: $ENV"

# ✅ Function to sync S3 with error handling
sync_s3() {
    local EID_CID=$1
    echo "🚀 Syncing ${EID_CID}..."

    if ! aws s3 sync "${SOURCE_BUCKET}/${EID_CID}/" "${DEST_BUCKET}/${DATE}/${EID_CID}" \
        --delete --region "${REGION}" | tee -a "logs/${EID_CID}.log"; then
        echo "❌ Error syncing ${EID_CID}. Check logs/${EID_CID}.log"
    fi
}

# ✅ Run jobs in parallel safely
SEMAPHORE=$(mktemp)
mkfifo "$SEMAPHORE"
exec 3<>"$SEMAPHORE"
rm "$SEMAPHORE"

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

echo "✅ All sync operations completed."
