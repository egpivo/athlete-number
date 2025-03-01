import os
from datetime import datetime
from io import BytesIO

import boto3
import pandas as pd
import pg8000
import streamlit as st
from dotenv import load_dotenv
from PIL import Image

# ✅ Load environment variables
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


def fetch_random_sample(cutoff_date):
    """Fetch a random EID, CID, and Photonum from PostgreSQL."""
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
        SELECT eid, cid, photonum FROM allsports_bib_number_detection
        WHERE cutoff_date = %s
        ORDER BY RANDOM()
        LIMIT 1;
        """
        cursor.execute(query, (cutoff_date,))
        row = cursor.fetchone()

        return row if row else None

    except Exception as e:
        st.error(f"❌ Error fetching random sample: {e}")
        return None
    finally:
        if conn:
            conn.close()


def fetch_results_from_postgres(cutoff_date, eid, cid, photonum, env):
    """Fetch detection results (EID, CID, Photonum, grouped Tags) from PostgreSQL."""
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
        SELECT eid, cid, photonum, array_agg(tag) AS tags
        FROM allsports_bib_number_detection
        WHERE cutoff_date = %s AND env = %s
        AND eid = %s AND cid = %s AND photonum = %s
        GROUP BY eid, cid, photonum
        """
        cursor.execute(query, (cutoff_date, env, eid, cid, photonum))
        rows = cursor.fetchall()

        return pd.DataFrame(rows, columns=["EID", "CID", "Photonum", "Tags"])

    except Exception as e:
        st.error(f"❌ Error fetching detection results: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def fetch_image_keys_from_postgres(cutoff_date, eid, cid, photonum, env):
    """Fetch all image keys from PostgreSQL for a given EID, CID, and Photonum."""
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
        SELECT image_key FROM athlete_number_detection_processed_image
        WHERE cutoff_date = %s AND env = %s
        AND image_key ILIKE %s
        ORDER BY image_key
        """
        search_pattern = f"images/{cutoff_date}/{eid}_{cid}/{eid}_{cid}_{photonum}_%"

        cursor.execute(query, (cutoff_date, env, search_pattern))
        rows = cursor.fetchall()

        return [row[0] for row in rows]

    except Exception as e:
        st.error(f"❌ Error fetching image keys: {e}")
        return []
    finally:
        if conn:
            conn.close()


def load_image_from_s3(image_key):
    """Load an image from S3 given its key."""
    try:
        response = s3.get_object(Bucket=S3_BUCKET_NAME, Key=image_key)
        return Image.open(BytesIO(response["Body"].read()))
    except Exception as e:
        st.error(f"❌ Error loading image: {e}")
        return None


# Streamlit UI
st.title("📸 Bib Number Detection Viewer")

st.markdown(
    """
    Use this tool to **verify  athlete detection results** stored in **PostgreSQL** and **preview images** from **AWS S3**.
    """
)

# Sidebar Inputs (Mandatory Fields)
st.sidebar.header("🔍 Search Filters")
today_date = datetime.today().strftime("%Y-%m-%d")
cutoff_date = st.sidebar.text_input("📅 Enter cutoff date (YYYY-MM-DD):", today_date)
eid = st.sidebar.text_input("🏅 Enter EID (Required):", "")
cid = st.sidebar.text_input("🎽 Enter CID (Required):", "")
photonum = st.sidebar.text_input("📸 Enter Photonum (Required):", "")
env = st.sidebar.selectbox("🌍 Select Environment:", ["production", "test"], index=0)
# Buttons for triggering search
trigger_search = False

# Sample Button - Picks a random EID, CID, Photonum & Auto-Runs Query
if st.sidebar.button("🎲 Pick Random Sample"):
    sample = fetch_random_sample(cutoff_date)
    if sample:
        eid, cid, photonum = sample
        st.session_state["eid"] = eid
        st.session_state["cid"] = cid
        st.session_state["photonum"] = photonum
        st.sidebar.success(
            f"✅ Picked Sample: EID={eid}, CID={cid}, Photonum={photonum}"
        )
        st.rerun()  # 🔄 Reload Streamlit
    else:
        st.sidebar.warning("⚠️ No sample found.")

# Manual Query Button
if st.sidebar.button("🔍 Query Results"):
    st.session_state["eid"] = eid
    st.session_state["cid"] = cid
    st.session_state["photonum"] = photonum
    st.rerun()  # 🔄 Reload Streamlit

# Only run the query if triggered by button clicks
if (
    "eid" in st.session_state
    and "cid" in st.session_state
    and "photonum" in st.session_state
):
    eid = st.session_state["eid"]
    cid = st.session_state["cid"]
    photonum = st.session_state["photonum"]

    # Fetch detection results (eid, cid, photonum, grouped tags)
    results_df = fetch_results_from_postgres(cutoff_date, eid, cid, photonum, env)

    if not results_df.empty:
        st.success(f"✅ Found {len(results_df)} results.")

        # Display results
        st.subheader("📊 Detection Results")
        st.dataframe(results_df)

        # Image Preview
        st.subheader("🖼️ Image Previews")

        image_keys = fetch_image_keys_from_postgres(
            cutoff_date, eid, cid, photonum, env
        )

        if image_keys:
            st.write(f"🔍 **Found {len(image_keys)} images for this athlete**")

            # Paginate image display
            page_size = 10
            total_pages = (len(image_keys) + page_size - 1) // page_size
            page_number = st.number_input(
                "📄 Page", min_value=1, max_value=total_pages, value=1, step=1
            )

            start_idx = (page_number - 1) * page_size
            end_idx = min(start_idx + page_size, len(image_keys))

            cols = st.columns(5)  # Display images in 5-column layout
            for i, img_key in enumerate(image_keys[start_idx:end_idx]):
                with cols[i % 5]:  # Distribute images across columns
                    img = load_image_from_s3(img_key)
                    if img:
                        st.image(
                            img,
                            caption=os.path.basename(
                                img_key
                            ),  # Show filename as footnote
                            use_container_width=True,
                        )
        else:
            st.warning(
                f"⚠️ No image found for EID: {eid}, CID: {cid}, Photonum: {photonum}"
            )
    else:
        st.warning("⚠️ No results found for the given criteria.")
