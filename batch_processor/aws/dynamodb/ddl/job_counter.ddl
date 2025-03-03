{
    "TableName": "athlete_number_detection_job_counter",
    "AttributeDefinitions": [
        { "AttributeName": "customer_id", "AttributeType": "S" },
        { "AttributeName": "job_id", "AttributeType": "S" }
    ],
    "KeySchema": [
        { "AttributeName": "customer_id", "KeyType": "HASH" },
        { "AttributeName": "job_id", "KeyType": "RANGE" }
    ],
    "BillingMode": "PAY_PER_REQUEST"
}
