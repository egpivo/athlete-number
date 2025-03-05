import os
import re

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from src.config import OUTPUT_CSV

# Load environment variables
load_dotenv()

# Database connection details from .env
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PW = os.getenv("DB_PW")

# Table Name
TABLE_NAME = "allsports_bib_number_detection"


def process_results(results):
    """Convert OCR results into structured format."""
    unique_rows = set()

    for result in results:
        eid, cid, photonum = result.filename.split("/")[-1].split("_")[:3]

        if result.extracted_number:
            for tag in result.extracted_number:
                if re.fullmatch(r"\d{5}", tag):
                    unique_rows.add((eid, cid, photonum, tag))

    return list(unique_rows)


def save_results_to_postgres(results, cutoff_date, env):
    """Insert detection results into PostgreSQL with cutoff_date and env."""

    structured_results = process_results(results)

    if not structured_results:
        print("No data to insert.")
        return

    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PW
        )
        cur = conn.cursor()

        # Insert query using batch insert
        insert_query = f"""
        INSERT INTO {TABLE_NAME} (eid, cid, photonum, tag, cutoff_date, env)
        VALUES %s
        ON CONFLICT (eid, cid, photonum, tag, cutoff_date, env) DO UPDATE
        SET modified_at = NOW();
        """

        # Prepare data by adding cutoff_date and env to each record
        records = [
            (r[0], r[1], r[2], r[3], cutoff_date, env) for r in structured_results
        ]

        # Batch insert data
        execute_values(cur, insert_query, records)

        # Commit changes
        conn.commit()
        cur.close()
        conn.close()

        print(
            f"✅ Successfully inserted/updated {len(records)} records into {TABLE_NAME}"
        )

    except Exception as e:
        print(f"❌ Error inserting data into PostgreSQL: {e}")


def save_results_to_csv(results):
    """Append detection results to a CSV file."""
    structured_results = process_results(results)
    df = pd.DataFrame(structured_results, columns=["eid", "cid", "photonum", "tag"])

    df.to_csv(OUTPUT_CSV, mode="a", index=False, header=not os.path.exists(OUTPUT_CSV))

    print(f"Results saved to {OUTPUT_CSV}")
