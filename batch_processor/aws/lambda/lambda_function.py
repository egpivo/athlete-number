import csv
import os
import tempfile
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
import pg8000
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# AWS SES Configuration
ses = boto3.client("ses", region_name="us-east-1")
SENDER_EMAIL = "joseph.wang@instai.co"
RECIPIENT_EMAILS = [
    "joseph.wang@instai.co",
    "honami@photocreate.com.tw",
    "keyu.pi@instai.co",
    "justin.chang@instai.co",
    "yingling.yang@instai.co",
]
TEST_SUBJECT = "[InstAI] Bib Number Detection Report - TEST"
PRODUCTION_SUBJECT = "[InstAI] Bib Number Detection Report - PROCESSED IMAGES"

# PostgreSQL Connection Details (Loaded from .env)
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PW")
DB_PORT = int(os.getenv("DB_PORT", 5432))


def fetch_data(cutoff_date, env):
    """Fetch detection data from PostgreSQL using pg8000"""
    connection = None
    try:
        connection = pg8000.connect(
            host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS
        )
        cursor = connection.cursor()

        # Query to fetch all records with dynamic filtering
        query = """
        SELECT eid, cid, photonum, tag
        FROM allsports_bib_number_detection
        WHERE cutoff_date = %s AND env = %s
        """
        cursor.execute(query, (cutoff_date, env))
        rows = cursor.fetchall()

        # Convert data into a list of dictionaries
        data = [
            {"eid": row[0], "cid": row[1], "photonum": row[2], "tag": row[3]}
            for row in rows
        ]

        return data
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return []
    finally:
        if connection:
            connection.close()


def generate_csv(data):
    """Generate CSV from PostgreSQL query results"""
    temp_dir = tempfile.gettempdir()
    csv_file = os.path.join(temp_dir, "report.csv")

    with open(csv_file, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    return csv_file


def get_processed_image_count(cutoff_date):
    """Retrieve the total count of processed images from PostgreSQL."""
    connection = None
    try:
        connection = pg8000.connect(
            host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS
        )
        cursor = connection.cursor()

        # Query to count processed images based on the cutoff_date
        query = """
        SELECT COUNT(*)
        FROM athlete_number_detection_processed_image
        WHERE cutoff_date = %s
        """
        cursor.execute(query, (cutoff_date,))
        count = cursor.fetchone()[0]  # Extract the count value

        print(f"✅ Total processed images for {cutoff_date}: {count}")
        return count
    except Exception as e:
        print(f"❌ Error counting processed images: {e}")
        return 0
    finally:
        if connection:
            connection.close()


def send_email(csv_file, env, cutoff_date):
    """Send email with CSV attachment via AWS SES to multiple recipients."""
    # Get the total number of processed images
    total_processed = get_processed_image_count(cutoff_date)

    # Prepare email content
    email_body = (
        f"Dear Customer,\n\n"
        f"The athlete number detection process on {cutoff_date} is currently in progress.\n\n"
        f"📸 Images processed so far: {total_processed}\n"
        f"⏳ Processing status: 🔄 In Progress\n\n"
        f"We are continuously updating the results and will notify you once the process is fully completed.\n\n"
        f"Please let us know if you have any questions or need further assistance.\n\n"
        f"Best Regards,\n"
        f"InstAI"
    )

    with open(csv_file, "rb") as file:
        csv_data = file.read()

    # Create email
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(RECIPIENT_EMAILS)  # Multiple recipients
    msg["Subject"] = TEST_SUBJECT if env == "test" else PRODUCTION_SUBJECT
    msg.attach(MIMEText(email_body, "plain"))

    # Attach CSV file
    part = MIMEBase("application", "octet-stream")
    part.set_payload(csv_data)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment; filename=report.csv")
    msg.attach(part)

    # Send email via SES
    response = ses.send_raw_email(
        Source=SENDER_EMAIL,
        Destinations=RECIPIENT_EMAILS,
        RawMessage={"Data": msg.as_string()},
    )

    print(
        f"✅ Email sent to {', '.join(RECIPIENT_EMAILS)}! Message ID: {response['MessageId']}"
    )


def lambda_handler(event, context):
    """Main Lambda function"""
    cutoff_date = event.get("cutoff_date", "2025-02-28")  # Default if not provided
    env = event.get("env", "test")  # Default to 'test' if not provided

    print(f"🔍 Fetching data for cutoff_date={cutoff_date}, env={env}")

    data = fetch_data(cutoff_date, env)
    if not data:
        print("⚠️ No data found.")
        return {"statusCode": 200, "body": "No data to send"}

    csv_file = generate_csv(data)
    send_email(csv_file, env, cutoff_date)

    return {"statusCode": 200, "body": "CSV email sent successfully"}
