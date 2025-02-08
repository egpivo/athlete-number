# Use a minimal Python base image
FROM python:3.10-slim AS backend

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    curl \
    lsof && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.8.2
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    echo "export PATH=/root/.local/bin:$PATH" >> /root/.bashrc

# Ensure Poetry is in PATH
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml poetry.lock* /app/

# Install dependencies using Poetry
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Copy application source code
COPY . /app/

# Expose the application port
EXPOSE 5566

# Start the application
CMD ["bash", "/app/scripts/start.sh"]
