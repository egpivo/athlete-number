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
├── backend/         # Backend service (YOLO + OCR)
│   ├── athlete_number/  # Core logic (detection, OCR, API)
│   ├── models/      # Pretrained model files
│   ├── tests/       # Unit tests
│   ├── scripts/     # Startup scripts
│   ├── pyproject.toml  # Poetry dependencies
│   ├── Dockerfile.cpu / Dockerfile.gpu
│   └── README.md
│
├── frontend/        # Streamlit-based UI for testing
│   ├── demo.py      # Main UI script
│   ├── artifact/    # Demo images
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
│
├── Makefile         # CLI commands for managing services
├── docker-compose.yaml  # Docker service definitions
└── README.md        # This file
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
