import logging
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key
from src.config import CUSTOMER_USAGE_TABLE, IMAGE_TRACKER_TABLE, JOB_COUNTER_TABLE

logger = logging.getLogger()
dynamodb = boto3.resource("dynamodb")


def is_duplicate_image(customer_id, image_id):
    """Check if an image has already been processed using IMAGE_TRACKER_TABLE."""
    try:
        table = dynamodb.Table(IMAGE_TRACKER_TABLE)

        # Normalize image_id to avoid case inconsistencies
        normalized_image_id = image_id.lower()  # Adjust if necessary

        logger.info(
            f"🔍 Checking duplicate for {normalized_image_id} - Customer: {customer_id}"
        )

        # Use Query with ConsistentRead for accurate results
        response = table.query(
            KeyConditionExpression=Key("customer_id").eq(customer_id)
            & Key("image_id").eq(normalized_image_id),
            ConsistentRead=True,  # Ensures up-to-date data
        )

        is_duplicate = "Items" in response and len(response["Items"]) > 0

        logger.info(
            f"✅ Duplicate Check Result for {normalized_image_id}: {is_duplicate}"
        )
        return is_duplicate

    except Exception as e:
        logger.error(f"❌ Error checking duplicate image: {str(e)}", exc_info=True)
        return False


def update_customer_usage(customer_id, images_processed):
    """Update total_images_processed and modified_at timestamp in DynamoDB."""
    try:
        table = dynamodb.Table(CUSTOMER_USAGE_TABLE)
        current_timestamp = datetime.now(timezone.utc).isoformat()

        # Step 1: Ensure images_processed is an integer
        if not isinstance(images_processed, int):
            logger.error(
                f"❌ images_processed must be an integer, received: {type(images_processed)}"
            )
            return

        # Step 2: Increment total_images_processed
        response = table.update_item(
            Key={"customer_id": customer_id},
            UpdateExpression="ADD total_images_processed :inc",
            ExpressionAttributeValues={
                ":inc": images_processed  # Ensuring it's an integer
            },
            ReturnValues="UPDATED_NEW",
        )

        logger.info(
            f"✅ Updated usage for '{customer_id}': {response.get('Attributes')}"
        )

        # Step 3: Update modified_at separately
        response = table.update_item(
            Key={"customer_id": customer_id},
            UpdateExpression="SET modified_at = :timestamp",
            ExpressionAttributeValues={
                ":timestamp": current_timestamp  # Store as a string (S type)
            },
            ReturnValues="UPDATED_NEW",
        )

        logger.info(f"✅ Updated modified_at timestamp for '{customer_id}'")

    except Exception as e:
        logger.error(f"❌ Error updating customer usage: {str(e)}", exc_info=True)


def update_job_counter(customer_id, job_id, images_processed, batch_size):
    """Ensure job counter exists and update total_images_processed with modified timestamp."""
    try:
        table = dynamodb.Table(JOB_COUNTER_TABLE)
        current_timestamp = datetime.now(timezone.utc).isoformat()

        # Ensure `images_processed` is an integer
        if not isinstance(images_processed, int):
            logger.error(
                f"❌ images_processed must be an integer, received: {type(images_processed)}"
            )
            return job_id  # Return the same job_id without modification

        # Step 1: Fetch current job count
        response = table.get_item(Key={"customer_id": customer_id, "job_id": job_id})
        current_total = int(response.get("Item", {}).get("total_images_processed", 0))

        # Step 2: Calculate new total count
        new_total = current_total + images_processed

        # Step 3: If new total still fits within batch size, update the same job_id
        if new_total <= batch_size:
            table.update_item(
                Key={"customer_id": customer_id, "job_id": job_id},
                UpdateExpression="SET total_images_processed = :new_total, modified_at = :timestamp",
                ExpressionAttributeValues={
                    ":new_total": new_total,
                    ":timestamp": current_timestamp,
                },
                ReturnValues="UPDATED_NEW",
            )
            logger.info(
                f"✅ Updated job '{job_id}' with {images_processed} new images (Total: {new_total})."
            )
            return job_id  # Keep the same job_id

        # Step 4: If new_total exceeds batch size, create a new job_id
        logger.info(f"🚀 Job '{job_id}' exceeded {batch_size}. Creating a new job ID...")
        new_job_id = f"{job_id.split('-')[0]}-{int(job_id.split('-')[-1]) + 1:02d}"

        # Insert new job counter entry
        table.put_item(
            Item={
                "customer_id": customer_id,
                "job_id": new_job_id,
                "total_images_processed": images_processed,  # Start fresh for new job
                "modified_at": current_timestamp,
            }
        )

        logger.info(f"✅ Created new job '{new_job_id}' with {images_processed} images.")
        return new_job_id  # Return the newly created job_id

    except Exception as e:
        logger.error(f"❌ Error updating job counter: {str(e)}", exc_info=True)
        return job_id  # Return the same job_id without modification


def update_image_tracker(image_id, customer_id, file_key, job_id):
    """Insert an image tracking record into DynamoDB."""
    try:
        table = dynamodb.Table(IMAGE_TRACKER_TABLE)
        current_timestamp = datetime.now(timezone.utc).isoformat()
        table.put_item(
            Item={
                "image_id": image_id,  # ✅ Fixed to use image_id as the sort key
                "customer_id": customer_id,
                "file_key": file_key,  # Keeping this in attributes, but not as key
                "timestamp": current_timestamp,
                "job_id": job_id,
            }
        )
        logger.info(f"✅ Image tracking recorded for {image_id}")
    except Exception as e:
        logger.error(f"❌ Error updating image tracker: {str(e)}", exc_info=True)


def get_customer_usage(customer_id):
    """Fetch the customer's contract details from DynamoDB."""
    try:
        table = dynamodb.Table(CUSTOMER_USAGE_TABLE)
        response = table.get_item(Key={"customer_id": customer_id})

        if "Item" not in response:
            logger.error(f"❌ No contract data found for customer '{customer_id}'.")
            return None

        contract_data = response["Item"]
        return {
            "end_date": contract_data.get("end_date"),
            "total_images_processed": int(
                contract_data.get("total_images_processed", 0)
            ),
            "contract_limit": int(contract_data.get("contract_limit", 0)),
        }

    except Exception as e:
        logger.error(f"❌ Error fetching contract data: {str(e)}", exc_info=True)
        return None


def update_job_counter(customer_id, job_id, images_processed, batch_size):
    """Ensure job counter exists and update total_images_processed correctly."""
    try:
        table = dynamodb.Table(JOB_COUNTER_TABLE)
        current_timestamp = datetime.now(timezone.utc).isoformat()

        # Ensure images_processed is an integer
        if not isinstance(images_processed, int):
            logger.error(
                f"❌ images_processed must be an integer, received: {type(images_processed)}"
            )
            return job_id  # Return the same job_id without modification

        # Step 1: Fetch current job count
        response = table.get_item(Key={"customer_id": customer_id, "job_id": job_id})
        job_item = response.get("Item", {})
        current_total = int(job_item.get("total_images_processed", 0))

        # Step 2: Determine new total count
        new_total = current_total + images_processed

        # Step 3: If new_total is within batch_size, update the same job_id
        if new_total <= batch_size:
            table.update_item(
                Key={"customer_id": customer_id, "job_id": job_id},
                UpdateExpression="SET total_images_processed = :new_total, modified_at = :timestamp",
                ExpressionAttributeValues={
                    ":new_total": new_total,
                    ":timestamp": current_timestamp,
                },
                ReturnValues="UPDATED_NEW",
            )
            logger.info(
                f"✅ Updated job '{job_id}' with {images_processed} new images (Total: {new_total})."
            )
            return job_id  # Keep the same job_id

        # Step 4: If new_total exceeds batch_size, create a new job_id for the remaining images
        logger.info(
            f"🚀 Job '{job_id}' reached {current_total} images. Creating a new job ID..."
        )
        new_job_id = f"{job_id.split('-')[0]}-{int(job_id.split('-')[-1]) + 1:02d}"

        # Calculate remaining images for the new job
        new_job_images = new_total - batch_size

        # Update the original job to store only batch_size images
        table.update_item(
            Key={"customer_id": customer_id, "job_id": job_id},
            UpdateExpression="SET total_images_processed = :batch_size, modified_at = :timestamp",
            ExpressionAttributeValues={
                ":batch_size": batch_size,
                ":timestamp": current_timestamp,
            },
            ReturnValues="UPDATED_NEW",
        )

        # Insert new job counter entry
        table.put_item(
            Item={
                "customer_id": customer_id,
                "job_id": new_job_id,
                "total_images_processed": new_job_images,  # Start with remaining images
                "modified_at": current_timestamp,
            }
        )

        logger.info(f"✅ Created new job '{new_job_id}' with {new_job_images} images.")
        return new_job_id  # Return the new job_id

    except Exception as e:
        logger.error(f"❌ Error updating job counter: {str(e)}", exc_info=True)
        return job_id  # Return the same job_id without modification


def get_next_job_id(customer_id, today_date, batch_size):
    """Retrieve the correct job_id for today, ensuring we reuse the last job if space is available."""
    try:
        table = dynamodb.Table(JOB_COUNTER_TABLE)

        # Fetch all job_ids for today
        response = table.scan(
            FilterExpression="customer_id = :cid AND begins_with(job_id, :date_prefix)",
            ExpressionAttributeValues={":cid": customer_id, ":date_prefix": today_date},
        )

        existing_jobs = sorted(response.get("Items", []), key=lambda x: x["job_id"])

        if not existing_jobs:
            return f"{today_date}-01"  # First job for today

        # Get the last job
        last_job = existing_jobs[-1]
        last_job_id = last_job["job_id"]
        last_job_total = int(last_job.get("total_images_processed", 0))

        # If last job has room, use the same job_id
        if last_job_total < batch_size:
            return last_job_id

        # Otherwise, create a new job ID
        last_batch_number = int(last_job_id.split("-")[-1])
        next_batch_number = last_batch_number + 1
        return f"{today_date}-{next_batch_number:02d}"

    except Exception as e:
        logger.error(f"❌ Error retrieving job_id: {str(e)}", exc_info=True)
        return f"{today_date}-01"


def batch_update_image_tracker(customer_id, file_list, job_id):
    table = dynamodb.Table(IMAGE_TRACKER_TABLE)

    if not file_list:
        logger.warning("⚠️ No files to update in image tracker.")
        return

    try:
        with table.batch_writer() as batch:
            for image_id in file_list:
                batch.put_item(
                    Item={
                        "customer_id": customer_id,
                        "image_id": image_id,
                        "job_id": job_id,
                    }
                )
        logger.info(f"✅ Successfully updated {len(file_list)} images in image tracker.")
    except Exception as e:
        logger.error(f"❌ Failed to update image tracker: {str(e)}")
