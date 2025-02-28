import csv
import json
import logging
import os
import tempfile
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
import pg8000
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# ✅ Load environment variables
load_dotenv()

# ✅ AWS Clients
secrets_client = boto3.client("secretsmanager", region_name="us-east-1")
ses = boto3.client("ses", region_name="us-east-1")

# ✅ Email Configuration
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
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")

# ✅ PostgreSQL Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PW"),
    "port": int(os.getenv("DB_PORT", 5432)),
}

# ✅ Google Sheets Configuration
SECRET_NAME = "GoogleSheetsServiceAccountBibNumber"
SHEET_NAME = "instai-test"


# ✅ Retrieve Google Sheets Credentials
def get_google_sheets_credentials():
    """Retrieve Google Sheets credentials from AWS Secrets Manager."""
    try:
        response = secrets_client.get_secret_value(SecretId=SECRET_NAME)
        service_account_info = json.loads(response["SecretString"])
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        return credentials
    except Exception as e:
        logger.error(f"❌ Google Sheets credentials error: {e}")
        return None


# ✅ Log Email Status to Google Sheets
def save_csv_to_google_sheets(csv_file):
    """Upload CSV content to Google Sheets."""
    credentials = get_google_sheets_credentials()
    if not credentials:
        logger.error("⚠️ Google Sheets credentials missing. Skipping CSV upload.")
        return

    try:
        service = build("sheets", "v4", credentials=credentials)
        sheet = service.spreadsheets()

        with open(csv_file, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            data = []
            for row in reader:
                try:
                    row = [int(cell) for cell in row]
                except ValueError:
                    pass
                data.append(row)

        row_count = len(data) - 1
        logger.info(f"📊 CSV Row Count (excluding header): {row_count}")

        body = {"values": data}
        sheet.values().clear(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=f"{SHEET_NAME}!B:Z",  # Clears all columns in the sheet
        ).execute()
        sheet.values().append(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=f"{SHEET_NAME}!B1",
            valueInputOption="RAW",
            body=body,
        ).execute()

        logger.info(f"✅ CSV data successfully uploaded to Google Sheets.")
    except Exception as e:
        logger.info(f"❌ Error uploading CSV to Google Sheets: {e}")


# ✅ Fetch Detection Data from PostgreSQL
def fetch_data(cutoff_date, env):
    """Fetch detection data from PostgreSQL."""
    try:
        with pg8000.connect(**DB_CONFIG) as conn:
            cursor = conn.cursor()
            query = """
            SELECT eid, cid, photonum, tag
            FROM allsports_bib_number_detection
            WHERE cutoff_date = %s AND env = %s AND tag <> ''
            """
            cursor.execute(query, (cutoff_date, env))
            return [
                {"eid": row[0], "cid": row[1], "photonum": row[2], "tag": row[3]}
                for row in cursor.fetchall()
            ]
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return []


# ✅ Generate CSV Report
def generate_csv(data):
    """Generate CSV from PostgreSQL query results."""
    temp_dir = tempfile.gettempdir()
    csv_file = os.path.join(temp_dir, "report.csv")

    with open(csv_file, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    return csv_file


# ✅ Get Count of Processed Images
def get_processed_image_count(cutoff_date):
    """Retrieve the total count of processed images from PostgreSQL."""
    try:
        with pg8000.connect(**DB_CONFIG) as conn:
            cursor = conn.cursor()
            query = "SELECT COUNT(*) FROM athlete_number_detection_processed_image WHERE cutoff_date = %s"
            cursor.execute(query, (cutoff_date,))
            count = cursor.fetchone()[0]

        logger.info(f"✅ Processed images for {cutoff_date}: {count}")
        return count
    except Exception as e:
        logger.error(f"❌ Error counting processed images: {e}")
        return 0


# ✅ Send Email with CSV Attachment
def send_email(csv_file, env, cutoff_date):
    """Send email with CSV attachment via AWS SES."""
    total_processed = get_processed_image_count(cutoff_date)

    email_body = (
        f"Dear Customer,\n\n"
        f"The athlete number detection process on {cutoff_date} is currently in progress.\n\n"
        f"📸 Images processed so far: {total_processed}\n"
        f"⏳ Processing status: 🔄 In Progress\n\n"
        f"We will notify you once the process is fully completed.\n\n"
        f"Best Regards,\nInstAI"
    )

    with open(csv_file, "rb") as file:
        csv_data = file.read()

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(RECIPIENT_EMAILS)
    msg["Subject"] = TEST_SUBJECT if env == "test" else PRODUCTION_SUBJECT
    msg.attach(MIMEText(email_body, "plain"))

    part = MIMEBase("application", "octet-stream")
    part.set_payload(csv_data)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment; filename=report.csv")
    msg.attach(part)

    try:
        response = ses.send_raw_email(
            Source=SENDER_EMAIL,
            Destinations=RECIPIENT_EMAILS,
            RawMessage={"Data": msg.as_string()},
        )
        logger.info(f"✅ Email sent! Message ID: {response['MessageId']}")
    except Exception as e:
        logger.error(f"❌ Email sending failed: {e}")


# ✅ AWS Lambda Handler
def lambda_handler(event, context):
    """Main Lambda function."""
    cutoff_date = event.get("cutoff_date", "2025-02-28")
    env = event.get("env", "test")

    logger.info(f"🔍 Processing for cutoff_date={cutoff_date}, env={env}")

    data = fetch_data(cutoff_date, env)
    if not data:
        logger.error("⚠️ No data found.")
        return {"statusCode": 200, "body": "No data to send"}

    csv_file = generate_csv(data)
    save_csv_to_google_sheets(csv_file)
    send_email(csv_file, env, cutoff_date)

    return {"statusCode": 200, "body": f"CSV email sent successfully"}
