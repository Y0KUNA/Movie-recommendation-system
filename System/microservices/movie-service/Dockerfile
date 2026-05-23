# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy common utilities
COPY ../common /app/common

# Expose port
EXPOSE 5001

# Run application
CMD ["python", "app.py"]
