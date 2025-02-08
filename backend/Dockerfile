# Stage 1: Build dependencies
FROM python:3.10-slim AS builder

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    swig \
    cmake \
    lsof \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry properly
ENV POETRY_VERSION=1.8.2
RUN curl -sSL https://install.python-poetry.org | python3 -

# Ensure poetry is in PATH
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/

# Configure Poetry and install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Stage 2: Final minimal image
FROM python:3.10-slim

WORKDIR /app

# Install `lsof`
RUN apt-get update && apt-get install -y lsof curl && rm -rf /var/lib/apt/lists/*

# Copy Poetry from the builder stage
COPY --from=builder /root/.local /root/.local
COPY --from=builder /usr/local/bin/poetry /usr/local/bin/poetry
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /app /app

# Ensure Poetry is in the PATH in the final image
ENV PATH="/root/.local/bin:$PATH"

COPY . /app/

EXPOSE 5566

CMD ["bash", "/app/scripts/start.sh"]
