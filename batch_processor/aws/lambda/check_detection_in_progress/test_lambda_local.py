import json

from lambda_function import lambda_handler  # Import your Lambda function

# Define a test event (mock event as JSON)
test_event = {"cutoff_date": "2025-03-01", "env": "test"}

# Mock AWS Lambda context (you can leave it empty)
class LambdaContext:
    def __init__(self):
        self.function_name = "athlete_number_detection_s3_ingestion_event"
        self.memory_limit_in_mb = 128
        self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:athlete_number_detection_s3_ingestion_event"
        self.aws_request_id = "test-aws-request-id"


# Run the function locally
if __name__ == "__main__":
    response = lambda_handler(test_event, LambdaContext())
    print(json.dumps(response, indent=4))
