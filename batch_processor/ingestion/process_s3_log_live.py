import os
import re
import sys
import time
from datetime import datetime

import psycopg2
from dotenv import load_dotenv

# ✅ Load environment variables from .env
load_dotenv()

# ✅ Get cutoff_date from command-line argument
if (
    len(sys.argv) > 2
):  # sys.argv[0] = script name, sys.argv[1] = logs, sys.argv[2] = cutoff_date
    CUTOFF_DATE = sys.argv[2]  # Get cutoff_date from shell script
else:
    CUTOFF_DATE = datetime.now().strftime("%Y-%m-%d")  # Default to today

print(f"📅 Using cutoff_date: {CUTOFF_DATE}")

# PostgreSQL Connection Config
PG_HOST = os.getenv("DB_HOST")
PG_PORT = os.getenv("DB_PORT", "5432")
PG_DB = os.getenv("DB_NAME")
PG_USER = os.getenv("DB_USER")
PG_PASSWORD = os.getenv("DB_PW")

TABLE_NAME = "athlete_number_detection_ingestion"
LOG_DIR = sys.argv[1] if len(sys.argv) > 1 else "logs"

# ✅ Ensure the log directory exists
if not os.path.exists(LOG_DIR):
    print(f"❌ Log directory '{LOG_DIR}' does not exist. Exiting.")
    exit(1)

# ✅ PostgreSQL Connection
def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASSWORD
    )


# ✅ Extract filename from S3 sync log line
def extract_filename(log_line):
    match = re.search(
        r"to s3://[^/]+/(.*?)$", log_line
    )  # Extract only destination path
    if match:
        image_key = match.group(1)
        print(f"✅ Extracted image_key: {image_key}")
        return image_key
    return None


# ✅ Process log file in real-time
def monitor_logs():
    log_files = {f: open(os.path.join(LOG_DIR, f), "r") for f in os.listdir(LOG_DIR)}

    while True:
        for log_file, f in log_files.items():
            line = f.readline()
            if line:
                filename = extract_filename(line.strip())
                if filename:
                    insert_filename(filename, CUTOFF_DATE)  # Pass cutoff_date
        time.sleep(1)


# ✅ Insert filename into PostgreSQL
def insert_filename(filename, cutoff_date):
    conn = get_pg_connection()
    cursor = conn.cursor()

    query = f"""
        INSERT INTO {TABLE_NAME} (image_key, cutoff_date, ingestion_timestamp, status)
        VALUES (%s, %s, %s, 'pending')
        ON CONFLICT (image_key, cutoff_date) DO NOTHING;
    """

    try:
        cursor.execute(query, (filename, cutoff_date, datetime.now()))
        conn.commit()
        print(f"✅ Inserted: {filename} (cutoff_date: {cutoff_date})")
    except Exception as e:
        print(f"❌ Error inserting {filename}: {e}")
    finally:
        cursor.close()
        conn.close()


# ✅ Run the script
if __name__ == "__main__":
    print(f"📡 Monitoring logs in {LOG_DIR} with cutoff_date {CUTOFF_DATE}...")
    monitor_logs()
