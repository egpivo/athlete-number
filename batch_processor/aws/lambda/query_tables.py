import boto3

# Initialize DynamoDB
dynamodb = boto3.resource("dynamodb")

# Table Names
CUSTOMER_USAGE_TABLE = "athlete_number_detection_customer_usage"
JOB_COUNTER_TABLE = "athlete_number_detection_job_counter"
IMAGE_TRACKER_TABLE = "athlete_number_detection_image_tracker"

customer_id = "allsports"  # Change as needed


def get_customer_status():
    """Fetch the customer's contract details from DynamoDB."""
    try:
        table = dynamodb.Table(CUSTOMER_USAGE_TABLE)
        response = table.get_item(Key={"customer_id": customer_id})

        if "Item" not in response:
            return f"❌ No contract data found for customer '{customer_id}'."

        contract_data = response["Item"]
        return {
            "customer_id": customer_id,
            "total_images_processed": contract_data.get("total_images_processed", 0),
            "contract_limit": contract_data.get("contract_limit", 0),
            "end_date": contract_data.get("end_date"),
        }

    except Exception as e:
        return f"❌ Error fetching contract data: {str(e)}"


def get_job_status():
    """Fetch all job counters for a customer."""
    try:
        table = dynamodb.Table(JOB_COUNTER_TABLE)
        response = table.scan(
            FilterExpression="customer_id = :cid",
            ExpressionAttributeValues={":cid": customer_id},
        )

        if "Items" not in response or not response["Items"]:
            return f"❌ No jobs found for customer '{customer_id}'."

        return sorted(response["Items"], key=lambda x: x["job_id"])

    except Exception as e:
        return f"❌ Error fetching job status: {str(e)}"


def get_image_tracker():
    """Fetch all image tracking records for a customer."""
    try:
        table = dynamodb.Table(IMAGE_TRACKER_TABLE)
        response = table.scan(
            FilterExpression="customer_id = :cid",
            ExpressionAttributeValues={":cid": customer_id},
        )

        if "Items" not in response or not response["Items"]:
            return f"❌ No images found for customer '{customer_id}'."

        return sorted(response["Items"], key=lambda x: x["timestamp"], reverse=True)

    except Exception as e:
        return f"❌ Error fetching image tracker: {str(e)}"


if __name__ == "__main__":
    print(get_image_tracker())
    print(get_job_status())
    print(get_customer_status())
