FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .

# Install dependencies (including requests which is used by deploy_tables.py but missing from requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt requests

# Copy the iceberg-kit directory
COPY iceberg-kit/ ./iceberg-kit/
COPY tpcds-kit/ ./tpcds-kit/
COPY benchmark-kit/ ./benchmark-kit/

# Set the working directory to where the script expects to run
WORKDIR /app

# Environment variables (override these when running the container)
# S3 Configuration
ENV S3_ENDPOINT_URL=http://localhost:9000
ENV S3_ACCESS_KEY=minioadmin
ENV S3_SECRET_KEY=minioadmin
ENV S3_BUCKET_NAME=tpcds
ENV S3_FOLDER_NAME=sample

# Iceberg Configuration
ENV ICEBERG_BUCKET_NAME=iceberg
ENV ICEBERG_FOLDER_NAME=sample
ENV ICEBERG_SUBFOLDER=

# Dremio Configuration
ENV DREMIO_USERNAME=
ENV DREMIO_PASSWORD=
ENV DREMIO_URL=http://localhost:9047
