FROM python:3.10-slim
LABEL authors="Joseph Wang <joseph.wang@instai.co>"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /frontend

RUN apt-get update && apt-get install -y curl wget && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first (to use Docker cache for dependencies)
COPY requirements.txt /frontend/

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the entire frontend source code
COPY . /frontend/

# Expose Streamlit port
EXPOSE 8501

# Download a sample digit image for backend warm-up
RUN wget -O /frontend/warmup.jpg https://upload.wikimedia.org/wikipedia/commons/2/27/MnistExamples.png

# Warm-up Backend Service with the Downloaded Image & Start Streamlit App
CMD sh -c "sleep 5 && curl -X POST http://backend:5566/extract/bib-numbers -F 'files=@/frontend/warmup.jpg' || echo '⚠ Backend warm-up failed' && streamlit run demo.py --server.port=8501 --server.address=0.0.0.0"
