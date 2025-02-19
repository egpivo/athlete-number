# Athlete-Number Frontend Detection

## **Prerequisites**
- **Python 3.10+**
- **Docker & Docker Compose**
- **Poetry** (if running locally)
  ```bash
  pip install poetry
  ```

## Folder Structure
```plantuml
athlete-number/
├── backend/         # Backend API (YOLO & OCR)
│   ├── athlete_number/
│   ├── models/
│   ├── tests/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── README.md
│
├── frontend/        # Web-based UI (Streamlit)
│   ├── demo.py
│   ├── artifact/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
│
├── batch_processor/ # Batch processing pipeline (S3 → API → CSV)
│   ├── detect_bib_numbers.py
│   ├── requirements.txt
│   ├── .env          # AWS credentials & API config
│   ├── logs/         # (Optional) Logs for batch runs
│   └── README.md
│
├── Makefile         # CLI commands for managing services
├── docker-compose.yaml  # Docker service definitions
└── README.md        # Main project README
```

## Start the System with Docker Compose
1. Build and Start
```bash
docker compose up --build -d
```
2. Check Logs
```bash
docker compose logs -f
```
3. Stop Services
```bash
docker compose down
```
