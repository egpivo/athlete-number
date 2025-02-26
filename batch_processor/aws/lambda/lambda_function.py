import csv
import os
import tempfile
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# AWS SES Configuration
ses = boto3.client("ses", region_name="us-east-1")
SENDER_EMAIL = "joseph.wang@instai.co"
RECIPIENT_EMAIL = "egpivo@gmail.com"
SUBJECT = "Athlete Number Detection Report"

# PostgreSQL Connection Details (Loaded from .env)
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PW")  # Make sure it's `DB_PW` and not `DB_PASS`
DB_PORT = os.getenv("DB_PORT", "5432")  # Default PostgreSQL port


def fetch_data():
    """Fetch detection data from PostgreSQL"""
    connection = None
    try:
        connection = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT
        )
        cursor = connection.cursor()

        # Query to fetch all records
        query = """
        SELECT eid, cid, photonum, tag
        FROM allsports_bib_number_detection
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        # Convert data into a list of dictionaries
        data = [
            {"eid": row[0], "cid": row[1], "photonum": row[2], "tag": row[3]}
            for row in rows
        ]

        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
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


def send_email(csv_file):
    """Send email with CSV attachment via AWS SES"""
    with open(csv_file, "rb") as file:
        csv_data = file.read()

    # Create email
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = SUBJECT
    msg.attach(
        MIMEText("Please find the attached athlete number detection report.", "plain")
    )

    # Attach CSV file
    part = MIMEBase("application", "octet-stream")
    part.set_payload(csv_data)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment; filename=report.csv")
    msg.attach(part)

    # Send email via SES
    response = ses.send_raw_email(
        Source=SENDER_EMAIL,
        Destinations=[RECIPIENT_EMAIL],
        RawMessage={"Data": msg.as_string()},
    )

    print(f"Email sent! Message ID: {response['MessageId']}")


def lambda_handler(event, context):
    """Main Lambda function"""
    data = fetch_data()
    if not data:
        print("No data found.")
        return {"statusCode": 200, "body": "No data to send"}

    csv_file = generate_csv(data)
    send_email(csv_file)

    return {"statusCode": 200, "body": "CSV email sent successfully"}


if __name__ == "__main__":
    data = fetch_data()
    if not data:
        print("No data found.")
    else:
        csv_file = generate_csv(data)
        send_email(csv_file)
        print("✅ CSV email sent successfully!")
