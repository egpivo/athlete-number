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

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# ✅ Load environment variables
load_dotenv()
# ✅ AWS Clients
secrets_client = boto3.client("secretsmanager", region_name="us-east-1")
ses_client = boto3.client("ses", region_name="us-east-1")
ec2_client = boto3.client("ec2", region_name="us-east-1")
events_client = boto3.client("events", region_name="us-east-1")
SECRET_NAME = "GoogleSheetsServiceAccountBibNumber"
SHEET_NAME = os.getenv("SHEET_NAME")

# ✅ PostgreSQL Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PW"),
    "port": int(os.getenv("DB_PORT", 5432)),
}
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")

# ✅ Email Configuration
SENDER_EMAIL = "joseph.wang@instai.co"
RECIPIENT_EMAILS = [
    "joseph.wang@instai.co",
    "honami@photocreate.com.tw",
    "keyu.pi@instai.co",
    "justin.chang@instai.co",
    "yingling.yang@instai.co",
]
FINAL_EMAIL_SUBJECT = "[InstAI] Bib Number Detection - Final Report"

# ✅ Detection Job Completion Criteria
THRESHOLD_MATCH_COUNT = 72000  # ✅ Stop job when 72000 images match


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


# ✅ Save CSV Content to Google Sheets
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
                    row = [int(cell) if cell.isdigit() else cell for cell in row]
                except ValueError:
                    pass
                data.append(row)

        row_count = len(data) - 1  # Exclude header
        logger.info(f"📊 CSV Row Count (excluding header): {row_count}")

        # ✅ Clear old data before updating
        sheet.values().clear(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=f"{SHEET_NAME}!A:Z",
        ).execute()

        # ✅ Append new CSV data
        sheet.values().append(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=f"{SHEET_NAME}!B1",
            valueInputOption="RAW",
            body={"values": data},
        ).execute()

        logger.info(f"✅ CSV data successfully uploaded to Google Sheets.")
    except Exception as e:
        logger.info(f"❌ Error uploading CSV to Google Sheets: {e}")


def fetch_data(cutoff_date):
    """Fetch detection data from PostgreSQL."""
    try:
        with pg8000.connect(**DB_CONFIG) as conn:
            cursor = conn.cursor()
            query = """
            SELECT eid, cid, photonum, tag
            FROM allsports_bib_number_detection
            WHERE cutoff_date = %s AND tag <> ''
            """
            cursor.execute(query, (cutoff_date,))
            return [
                {"eid": row[0], "cid": row[1], "photonum": row[2], "tag": row[3]}
                for row in cursor.fetchall()
            ]
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return []


def generate_csv(data):
    """Generate CSV from PostgreSQL query results."""
    temp_dir = tempfile.gettempdir()
    csv_file = os.path.join(temp_dir, "final_report.csv")

    with open(csv_file, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    return csv_file


def send_email(csv_file, cutoff_date):
    """Send final email with CSV attachment via AWS SES."""
    email_body = (
        f"Dear Customer,\n\n"
        f"The athlete number detection process for {cutoff_date} is now **fully completed**. 🎉\n\n"
        f"✅ The final report has been attached.\n"
        f"📊 The processed data is also available in Google Sheets.\n\n"
        f"Best Regards,\nInstAI"
    )

    with open(csv_file, "rb") as file:
        csv_data = file.read()

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(RECIPIENT_EMAILS)
    msg["Subject"] = FINAL_EMAIL_SUBJECT
    msg.attach(MIMEText(email_body, "plain"))

    part = MIMEBase("application", "octet-stream")
    part.set_payload(csv_data)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment; filename=final_report.csv")
    msg.attach(part)

    try:
        response = ses_client.send_raw_email(
            Source=SENDER_EMAIL,
            Destinations=RECIPIENT_EMAILS,
            RawMessage={"Data": msg.as_string()},
        )
        logger.info(f"✅ Final report email sent! Message ID: {response['MessageId']}")
    except Exception as e:
        logger.error(f"❌ Error sending final email: {e}")


def check_detection_completion(cutoff_date):
    try:
        with pg8000.connect(**DB_CONFIG) as conn:
            cursor = conn.cursor()

            # ✅ Count processed images
            cursor.execute(
                "SELECT COUNT(*) FROM athlete_number_detection_processed_image WHERE cutoff_date = %s",
                (cutoff_date,),
            )
            processed_images = cursor.fetchone()[0]

            logger.info(f"📊 Processed images: {processed_images}")

            return processed_images >= THRESHOLD_MATCH_COUNT
    except Exception as e:
        logger.error(f"❌ Error checking job status: {e}")
        return False


# ✅ Stop EC2 Instance
def stop_instance(instance_id):
    try:
        ec2_client.stop_instances(InstanceIds=[instance_id])
        logger.info(f"✅ EC2 Instance {instance_id} stopped successfully.")
    except Exception as e:
        logger.error(f"❌ Error stopping EC2 instance: {e}")


def disable_scheduler(rule_name):
    try:
        events_client.disable_rule(Name=rule_name)
        logger.info(f"✅ CloudWatch Scheduler {rule_name} disabled.")
    except Exception as e:
        logger.error(f"❌ Error disabling CloudWatch Scheduler: {e}")


# ✅ AWS Lambda Handler
def lambda_handler(event, context):
    cutoff_date = event.get("cutoff_date", "2025-02-28")
    instance_id = event.get("instance_id", "i-0afd9f4befb29399f")
    scheduler_rule1 = event.get("scheduler_rule1", "HourlyReportTrigger")
    scheduler_rule2 = event.get("scheduler_rule2", "check-detection-job")

    logger.info(f"🔍 Checking detection job status for {cutoff_date}...")

    if check_detection_completion(cutoff_date):
        logger.info("✅ Detection job completed!")
        data = fetch_data(cutoff_date)
        if not data:
            logger.error("⚠️ No data found for the final report.")
            return {"statusCode": 200, "body": "No data to send"}

        csv_file = generate_csv(data)
        save_csv_to_google_sheets(csv_file)
        # send_email(csv_file, cutoff_date)

        # ✅ Stop the EC2 instance
        stop_instance(instance_id)

        # ✅ Disable the scheduler
        disable_scheduler(scheduler_rule1)
        disable_scheduler(scheduler_rule2)

        return {
            "statusCode": 200,
            "body": "Final email sent, instance stopped, and scheduler disabled.",
        }
    else:
        logger.info("⏳ Detection job still in progress...")
        return {
            "statusCode": 200,
            "body": "Job not yet completed, will check again later.",
        }
