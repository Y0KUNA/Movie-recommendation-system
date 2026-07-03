# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements
COPY recommendation-service/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY recommendation-service/ .

# Copy common utilities
COPY common /app/common

# Expose port
EXPOSE 5002

# Run application
CMD ["python", "app.py"]
