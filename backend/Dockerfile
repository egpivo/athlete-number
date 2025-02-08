# Stage 1: Build dependencies
FROM python:3.10-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    swig \
    cmake \
    lsof \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && \
    pip install poetry gunicorn

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/

RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Stage 2: Final minimal image
FROM python:3.10-slim

WORKDIR /app

COPY --from=builder /app /app

COPY . /app/

RUN apt-get update && apt-get install -y lsof  # 🔥 Install lsof
RUN pip install gunicorn  # 🔥 Install Gunicorn again in final image

EXPOSE 5566

CMD ["bash", "/app/scripts/start.sh"]
