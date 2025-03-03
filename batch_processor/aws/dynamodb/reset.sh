 aws dynamodb update-item \
    --table-name athlete_number_detection_customer_usage \
    --key '{"customer_id": {"S": "allsports"}}' \
    --update-expression "SET total_images_processed = :zero" \
    --expression-attribute-values '{":zero": {"N": "0"}}' \
    --region us-east-1


aws dynamodb update-item \
    --table-name athlete_number_detection_customers \
    --key '{"customer_id": {"S": "allsports"}}' \
    --update-expression "SET contract_limit = :new_limit" \
    --expression-attribute-values '{":new_limit": {"N": "1000000"}}'
