{
    "TableName": "athlete_number_detection_image_processing_checkpoint",
    "AttributeDefinitions": [
        { "AttributeName": "bucket_name", "AttributeType": "S" }
    ],
    "KeySchema": [
        { "AttributeName": "bucket_name", "KeyType": "HASH" }
    ],
    "BillingMode": "PAY_PER_REQUEST"
}
