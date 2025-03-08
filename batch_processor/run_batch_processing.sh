#!/bin/bash

# Default Parameters
ENVIRONMENT="test"
LOCAL_DIR="./local_images"
BATCH_SIZE=20
PAGE_SIZE=50
MAX_IMAGES=10000
LOG_DIR="./logs"

usage() {
    echo "Usage: $0 -c <cutoff_date> [-e <environment>] [-l <local_dir>] [-b <batch_size>] [-p <page_size>] [-m <max_images>]"
    exit 1
}

# Parse arguments with getopt
while getopts "c:e:l:b:p:m:" opt; do
    case $opt in
        c) CUTOFF_DATE="$OPTARG";;
        e) ENVIRONMENT="$OPTARG";;
        l) LOCAL_DIR="$OPTARG";;
        b) BATCH_SIZE="$OPTARG";;
        p) PAGE_SIZE="$OPTARG";;
        m) MAX_IMAGES="$OPTARG";;
        *) usage;;
    esac
done

# Check if cutoff_date is provided
if [ -z "$CUTOFF_DATE" ]; then
    usage
fi

# Create log directory
mkdir -p "$LOG_DIR"

# Activate virtual environment (uncomment and adjust if necessary)
# source ./venv/bin/activate

# Run the Download Pipeline in the background
echo "🚀 Starting Image Download Pipeline..."
python download_bib_numbers.py \
    --cutoff_date "$CUTOFF_DATE" \
    --env "$ENVIRONMENT" \
    --batch_size "$PAGE_SIZE" \
    --local_dir "$LOCAL_DIR" \
    --max_images "$MAX_IMAGES" > "$LOG_DIR/download_${CUTOFF_DATE}_$(date +%Y%m%d_%H%M%S).log" 2>&1 &

DOWNLOAD_PID=$!
echo "Download job PID: $DOWNLOAD_PID"

# Wait for 2 minutes before starting OCR pipeline
sleep 60

# Run the Detection/OCR Pipeline in parallel
echo "🖥️ Starting OCR Detection Pipeline..."
python detect_bib_numbers.py \
    --cutoff_date "$CUTOFF_DATE" \
    --env "$ENVIRONMENT" \
    --batch_size "$BATCH_SIZE" \
    --local_dir "$LOCAL_DIR" > "$LOG_DIR/detection_${CUTOFF_DATE}_$(date +%Y%m%d_%H%M%S).log" 2>&1 &

DETECTION_PID=$!
echo "Detection job PID: $DETECTION_PID"

# Wait for both jobs to finish
wait $DOWNLOAD_PID
wait $DETECTION_PID

# Done
echo "🎉 Pipeline completed!"
