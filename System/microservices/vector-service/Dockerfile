# Use official Python runtime as base image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY vector-service/requirements.txt .

RUN pip install --no-cache-dir torch==2.2.2 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY vector-service/ .
COPY common /app/common

EXPOSE 5003

CMD ["python", "app.py"]
