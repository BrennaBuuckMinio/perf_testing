FROM python:3.11-slim

# Install Java runtime and curl for downloads
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-jre curl && \
    rm -rf /var/lib/apt/lists/*

# Install JMeter
ENV JMETER_VERSION=5.6.3
ENV JMETER_HOME=/opt/jmeter
ENV PATH="${JMETER_HOME}/bin:${PATH}"
ENV JVM_ARGS="-Dio.netty.tryReflectionSetAccessible=true --add-opens=java.base/java.nio=ALL-UNNAMED --add-opens=java.base/sun.nio.ch=ALL-UNNAMED"
RUN curl -fsSL https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-${JMETER_VERSION}.tgz | tar xz -C /opt && \
    mv /opt/apache-jmeter-${JMETER_VERSION} ${JMETER_HOME}

# Download Dremio JDBC driver into JMeter lib/
RUN curl -fsSL -o ${JMETER_HOME}/lib/dremio-jdbc-driver-LATEST.jar \
    https://download.dremio.com/jdbc-driver/dremio-jdbc-driver-LATEST.jar

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
