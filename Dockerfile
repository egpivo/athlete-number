FROM python:3.10-slim
LABEL authors="joseph"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    lsof \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --upgrade pip && \
    pip install poetry

# Set work directory
WORKDIR /app

# Copy only the poetry files to leverage Docker cache
COPY pyproject.toml poetry.lock* /app/

# Install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Copy application code (excluding venv because of .dockerignore)
COPY . /app/

# Make the start script executable
RUN chmod +x /app/scripts/start.sh

# Expose FastAPI port
EXPOSE 5566

# Run the application
CMD ["/app/scripts/start.sh"]
