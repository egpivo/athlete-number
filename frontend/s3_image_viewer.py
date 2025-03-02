import os
from datetime import datetime

import boto3
import pandas as pd
import pg8000
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS S3 Configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET", "athlete-number-detection")

# PostgreSQL Configuration
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = int(os.getenv("DB_PORT", 5432))

# Initialize AWS S3 Client
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)


def fetch_detection_stats(cutoff_date, env):
    """Fetch detection statistics from PostgreSQL."""
    try:
        conn = pg8000.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        cursor = conn.cursor()

        query = """
        WITH extracted_data AS (
            SELECT
                (regexp_matches(image_key, 'images/\d{4}-\d{2}-\d{2}/(\d+)_(\d+)/'))[1]::INT AS eid,
                (regexp_matches(image_key, 'images/\d{4}-\d{2}-\d{2}/(\d+)_(\d+)/'))[2]::INT AS cid,
                (regexp_matches(image_key, 'images/\d{4}-\d{2}-\d{2}/\d+_\d+/(\d+)_(\d+)_(\d+)_tn_'))[3]::INT AS photonum
            FROM athlete_number_detection_processed_image
            WHERE env = %s
              AND cutoff_date = %s
              AND image_key LIKE '%%_tn_%%'
              AND image_key NOT LIKE '%%_tnW%%'
        ),
        processed_photo AS (
            SELECT eid, cid, COUNT(DISTINCT photonum) AS processed_photonum_count
            FROM extracted_data
            GROUP BY eid, cid
        ),
        detected_photo AS (
            SELECT eid::INT AS eid, cid::INT AS cid, COUNT(DISTINCT photonum) AS detected_photonum_count
            FROM allsports_bib_number_detection
            WHERE env = %s
              AND cutoff_date = %s
            GROUP BY eid, cid
        )
        SELECT
            d.eid,
            d.cid,
            d.detected_photonum_count,
            COALESCE(p.processed_photonum_count, 0) AS processed_photonum_count,
            COALESCE(
                ROUND(
                    CASE
                        WHEN COALESCE(processed_photonum_count, 0) = 0 THEN 0  -- Avoid division by 0
                        ELSE detected_photonum_count::NUMERIC / processed_photonum_count::NUMERIC
                    END,
                3), 0.000  -- Ensure NULL → 0.000
            ) AS success_rate  -- Round to 3 decimal places
        FROM detected_photo d
        LEFT JOIN processed_photo p ON d.eid = p.eid AND d.cid = p.cid
        ORDER BY d.eid, d.cid;
        """
        cursor.execute(query, (env, cutoff_date, env, cutoff_date))
        rows = cursor.fetchall()

        return pd.DataFrame(
            rows,
            columns=["EID", "CID", "Detected Count", "Processed Count", "Success Rate"],
        )

    except Exception as e:
        st.error(f"❌ Error fetching stats: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


# Streamlit UI
st.set_page_config(page_title="Bib Number Detection Monitor", layout="wide")
st.sidebar.title("📋 Navigation")
page = st.sidebar.radio("Go to", ["Query Results", "Processing Stats"])

if page == "Query Results":
    st.title("📸 Bib Number Detection Viewer")
    st.markdown(
        """
        Use this tool to **verify athlete detection results** stored in **PostgreSQL** and **preview images** from **AWS S3**.
        """
    )

    # Sidebar Inputs
    st.sidebar.header("🔍 Search Filters")
    today_date = datetime.today().strftime("%Y-%m-%d")
    cutoff_date = st.sidebar.text_input("📅 Enter cutoff date (YYYY-MM-DD):", today_date)
    eid = st.sidebar.text_input("🏅 Enter EID (Required):", "")
    cid = st.sidebar.text_input("🎽 Enter CID (Required):", "")
    photonum = st.sidebar.text_input("📸 Enter Photonum (Required):", "")
    env = st.sidebar.selectbox("🌍 Select Environment:", ["production", "test"], index=0)

    # Query results implementation (same as before)
    # ...

elif page == "Processing Stats":
    st.title("📊 Detection & Processing Statistics")

    # Sidebar Inputs
    st.sidebar.header("🔍 Search Filters")
    today_date = datetime.today().strftime("%Y-%m-%d")
    cutoff_date = st.sidebar.text_input("📅 Enter cutoff date (YYYY-MM-DD):", today_date)
    env = st.sidebar.selectbox("🌍 Select Environment:", ["production", "test"], index=0)

    stats_df = fetch_detection_stats(cutoff_date, env)
    if not stats_df.empty:
        st.success(f"✅ Found {len(stats_df)} records.")
        st.dataframe(stats_df)
    else:
        st.warning("⚠️ No records found for the given date and environment.")

    if st.sidebar.button("🔄 Refresh Stats"):
        st.rerun()
