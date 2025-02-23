{
    "TableName": "athlete_number_detection_customer_usage",
    "AttributeDefinitions": [
        { "AttributeName": "customer_id", "AttributeType": "S" }
    ],
    "KeySchema": [
        { "AttributeName": "customer_id", "KeyType": "HASH" }
    ],
    "BillingMode": "PAY_PER_REQUEST"
}
