# Athlete-Number Detection - Batch Processing

## **Prerequisites**
- **Python 3.10+**
- **Poetry** (if running locally)
  ```bash
  pip install poetry
  ```
- - **AWS CLI** (for managing S3)
  ```bash
  curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
  unzip awscliv2.zip
  ./aws/install

  # Verify installation
  aws --version
  ```

## Usage
- The system dynamically selects the optimal batch size based on the OCR batch size (`OCR_BATCH_SIZE`).

```python
python detect_bib_numbers.py --max_images 100
```


## Table Query
- Customer Details
```bash
aws dynamodb get-item --table-name athlete_number_detection_customers \
    --key '{"customer_id": {"S": "allsports"}}' \
    --region us-east-1 --output json
```

- Customer Usage
```bash
aws dynamodb get-item --table-name athlete_number_detection_customer_usage \
    --key '{"customer_id": {"S": "allsports"}}' \
    --region us-east-1 --output json
```
