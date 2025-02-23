{
    "TableName": "athlete_number_detection_image_tracker",
    "AttributeDefinitions": [
        { "AttributeName": "customer_id", "AttributeType": "S" },
        { "AttributeName": "image_id", "AttributeType": "S" }
    ],
    "KeySchema": [
        { "AttributeName": "customer_id", "KeyType": "HASH" },
        { "AttributeName": "image_id", "KeyType": "RANGE" }
    ],
    "BillingMode": "PAY_PER_REQUEST"
}
