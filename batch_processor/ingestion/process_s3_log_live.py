import os
import re
import time
from datetime import datetime

import psycopg2
from dotenv import load_dotenv

# ✅ Load environment variables from .env
load_dotenv()

# PostgreSQL Connection Config
PG_HOST = os.getenv("DB_HOST")
PG_PORT = os.getenv("DB_PORT", "5432")
PG_DB = os.getenv("DB_NAME")
PG_USER = os.getenv("DB_USER")
PG_PASSWORD = os.getenv("DB_PW")


TABLE_NAME = "athlete_number_detection_images"
LOG_DIR = "logs"
# ✅ Ensure the log directory exists
if not os.path.exists(LOG_DIR):
    print(f"❌ Log directory '{LOG_DIR}' does not exist. Exiting.")
    exit(1)


# PostgreSQL Connection
def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASSWORD
    )


# Extract filename from S3 sync log line
def extract_filename(log_line):
    # ✅ Update regex to match "copy:" instead of "download:"
    match = re.search(r"copy: (.*?) to", log_line)
    if match:
        filename = match.group(1)
        print(f"✅ Extracted Filename: {filename}")  # Debug print
        return filename
    return None


# Process log file in real-time
def monitor_logs():
    log_files = {f: open(os.path.join(LOG_DIR, f), "r") for f in os.listdir(LOG_DIR)}

    while True:
        for log_file, f in log_files.items():
            line = f.readline()
            if line:
                filename = extract_filename(line.strip())
                if filename:
                    insert_filename(filename)
        time.sleep(1)


# Insert filename into PostgreSQL
def insert_filename(filename):
    conn = get_pg_connection()
    cursor = conn.cursor()

    query = f"""
        INSERT INTO {TABLE_NAME} (image_key, ingestion_timestamp, status)
        VALUES (%s, %s, 'pending')
        ON CONFLICT (image_key) DO NOTHING;
    """

    try:
        cursor.execute(query, (filename, datetime.now()))
        conn.commit()
        print(f"Inserted: {filename}")
    except Exception as e:
        print(f"Error inserting {filename}: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    print(f"Monitoring logs in {LOG_DIR}...")
    monitor_logs()
