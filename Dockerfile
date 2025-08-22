# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY garminsync/ ./garminsync/
COPY migrations/ ./migrations/
COPY tests/ ./tests/
COPY entrypoint.sh .
COPY patches/ ./patches/

# Fix garth package duplicate parameter issue
RUN cp patches/garth_data_weight.py /usr/local/lib/python3.10/site-packages/garth/data/weight.py

# Make the entrypoint script executable
RUN chmod +x entrypoint.sh

# Create data directory
RUN mkdir -p /app/data

# Set the entrypoint
ENTRYPOINT ["./entrypoint.sh"]

# Expose port
EXPOSE 8888
