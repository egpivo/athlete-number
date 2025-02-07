FROM python:3.10-slim
LABEL authors="Joseph Wang <joseph.wang@instai.co>"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /frontend

# Copy only the requirements file first (to use Docker cache for dependencies)
COPY requirements.txt /frontend/

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the entire frontend source code
COPY . /frontend/

# Expose Streamlit port
EXPOSE 8501

# Start Streamlit app
CMD ["streamlit", "run", "demo.py", "--server.port=8501", "--server.address=0.0.0.0"]
