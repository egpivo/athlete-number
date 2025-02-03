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
COPY pyproject.toml poetry.lock* athlete_number/ /app/

# Install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi  --no-root

# Copy the rest of the application code
COPY .env  models/ /app/
COPY scripts/start.sh /app/scripts/start.sh

# Expose the port FastAPI will run on
EXPOSE 5566

# Make the start script executable
RUN chmod +x /app/scripts/start.sh

# Command to run the application in production mode
CMD ["/app/scripts/start.sh"]
