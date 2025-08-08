# Use official Python base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY garminsync/ ./garminsync/

# Create data directory
RUN mkdir -p /app/data

# Set environment variables from .env file
ENV ENV_FILE=/app/.env
ENV DATA_DIR=/app/data

# Expose web UI port
EXPOSE 8080

# Update entrypoint to support daemon mode
ENTRYPOINT ["python", "-m", "garminsync.cli"]
CMD ["--help"]
