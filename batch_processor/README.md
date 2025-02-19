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
- Note: requiring a live API connection

```python
python detect_bib_numbers.py --max_images 100 --batch_size 20
```
