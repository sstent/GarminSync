# Use multi-stage build with pre-built scientific packages
FROM python:3.12-slim-bookworm as builder

# Install minimal build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel

# Install scientific packages first using pre-built wheels
RUN pip install --no-cache-dir --only-binary=all \
    numpy \
    scipy \
    pandas \
    scikit-learn

# Copy requirements and install remaining dependencies
COPY requirements.txt .

# Install remaining requirements, excluding packages we've already installed
RUN pip install --no-cache-dir \
    aiosqlite asyncpg aiohttp \
    $(grep -v '^numpy\|^scipy\|^pandas\|^scikit-learn' requirements.txt | tr '\n' ' ')

# Final runtime stage
FROM python:3.12-slim-bookworm

# Install only essential runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libgfortran5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application files
COPY garminsync/ ./garminsync/
COPY migrations/ ./migrations/
COPY migrations/alembic.ini ./alembic.ini
COPY tests/ ./tests/
COPY entrypoint.sh .
COPY patches/ ./patches/

# Apply patches
RUN cp patches/garth_data_weight.py /opt/venv/lib/python3.12/site-packages/garth/data/weight.py

# Set permissions
RUN chmod +x entrypoint.sh

# Create data directory
RUN mkdir -p /app/data

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8888/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
EXPOSE 8888