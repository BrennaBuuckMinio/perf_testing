#!/bin/bash
#
# Wrapper script that loads .env and runs JMeter with the correct JDBC properties.
#
# Usage:
#   ./run_benchmark.sh noref          # Run full benchmark without reflections
#   ./run_benchmark.sh wref           # Run full benchmark with reflections
#   ./run_benchmark.sh partial        # Run partial benchmark (4 queries x 3 iterations)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

echo ""
echo "==========================================================="
echo "  TPC-DS Benchmark Runner"
echo "==========================================================="
echo ""

# ---------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------
echo "[CONFIG] Loading environment from: $ENV_FILE"

if [ ! -f "$ENV_FILE" ]; then
    echo "[CONFIG] .env file not found at $ENV_FILE — skipping (using existing environment)"
else

while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)
    export "$key=$value"
done < "$ENV_FILE"

echo "[CONFIG] .env loaded successfully"
fi
echo ""

# ---------------------------------------------------------------
# Validate required variables
# ---------------------------------------------------------------
echo "[VALIDATE] Checking required environment variables..."

MISSING=0
for var in DREMIO_USERNAME DREMIO_PASSWORD DREMIO_JDBC_HOST NESSIE_SOURCE_NAME ICEBERG_FOLDER_NAME S3_ENDPOINT_URL S3_ACCESS_KEY S3_SECRET_KEY BENCHMARK_BUCKET; do
    if [ -z "${!var:-}" ]; then
        echo "[VALIDATE] MISSING: $var is not set in .env"
        MISSING=1
    else
        # Mask secrets in output
        if [[ "$var" = "DREMIO_PASSWORD" || "$var" = "S3_SECRET_KEY" ]]; then
            echo "[VALIDATE] OK: $var = ********"
        else
            echo "[VALIDATE] OK: $var = ${!var}"
        fi
    fi
done

if [ "$MISSING" -eq 1 ]; then
    echo ""
    echo "[ERROR] One or more required variables are missing. Exiting."
    exit 1
fi

echo "[VALIDATE] All required variables present"
echo ""

# ---------------------------------------------------------------
# Compose JDBC schema
# ---------------------------------------------------------------
JDBC_SCHEMA="\"${NESSIE_SOURCE_NAME}\".${ICEBERG_FOLDER_NAME}"
echo "[JDBC] Composed schema: ${JDBC_SCHEMA}"
echo "[JDBC] Connection URL: jdbc:dremio:direct=${DREMIO_JDBC_HOST}:${DREMIO_JDBC_PORT:-31010};disableTLS=true;schema=${JDBC_SCHEMA}"
echo ""

# ---------------------------------------------------------------
# Select test plan
# ---------------------------------------------------------------
MODE="${1:-}"

case "$MODE" in
    noref)
        TEST_PLAN="testplans/full_test_plan_noref.jmx"
        DESCRIPTION="Full 99-query benchmark WITHOUT reflections"
        ;;
    wref)
        TEST_PLAN="testplans/full_test_plan_wref.jmx"
        DESCRIPTION="Full 99-query benchmark WITH reflections"
        ;;
    partial)
        TEST_PLAN="testplans/partial_test_plan.jmx"
        DESCRIPTION="Quick test (4 queries x 3 iterations)"
        ;;
    *)
        echo "[ERROR] No test mode specified."
        echo ""
        echo "Usage: $0 {noref|wref|partial}"
        echo ""
        echo "  noref    - Full 99-query benchmark without reflections"
        echo "  wref     - Full 99-query benchmark with reflections"
        echo "  partial  - Quick test (4 queries x 3 iterations)"
        echo ""
        exit 1
        ;;
esac

# ---------------------------------------------------------------
# Compose results filename
# ---------------------------------------------------------------
TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
RESULTS_FILE="results/${ICEBERG_FOLDER_NAME}_${MODE}_${TIMESTAMP}.csv"
mkdir -p "$SCRIPT_DIR/results"

echo "==========================================================="
echo "  BENCHMARK CONFIGURATION"
echo "==========================================================="
echo "  Mode:       $MODE"
echo "  Plan:       $TEST_PLAN"
echo "  Desc:       $DESCRIPTION"
echo "  Host:       ${DREMIO_JDBC_HOST}"
echo "  Port:       ${DREMIO_JDBC_PORT:-31010}"
echo "  Username:   ${DREMIO_USERNAME}"
echo "  Schema:     ${JDBC_SCHEMA}"
echo "  Results:    ${RESULTS_FILE}"
echo "  Started:    $(date '+%Y-%m-%d %H:%M:%S')"
echo "==========================================================="
echo ""

# ---------------------------------------------------------------
# Run JMeter
# ---------------------------------------------------------------
echo "[JMETER] Starting JMeter..."
echo "[JMETER] Test plan: $TEST_PLAN"
echo "[JMETER] Results file: $RESULTS_FILE"
echo ""

cd "$SCRIPT_DIR"

START_TIME=$(date +%s)

jmeter -n -t "$TEST_PLAN" \
    -Jdremio.host="${DREMIO_JDBC_HOST}" \
    -Jdremio.port="${DREMIO_JDBC_PORT:-31010}" \
    -Jdremio.username="${DREMIO_USERNAME}" \
    -Jdremio.password="${DREMIO_PASSWORD}" \
    -Jdremio.schema="${JDBC_SCHEMA}" \
    -Jresults.file="${RESULTS_FILE}"

EXIT_CODE=$?
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

echo ""
echo "==========================================================="
echo "  BENCHMARK COMPLETE"
echo "==========================================================="
echo "  Mode:       $MODE"
echo "  Results:    $RESULTS_FILE"
echo "  Exit Code:  $EXIT_CODE"
echo "  Duration:   ${MINUTES}m ${SECONDS}s"
echo "  Finished:   $(date '+%Y-%m-%d %H:%M:%S')"
echo "==========================================================="

if [ "$EXIT_CODE" -eq 0 ]; then
    echo "[SUCCESS] Benchmark completed successfully!"
    echo "[SUCCESS] Results saved to: $RESULTS_FILE"
else
    echo "[FAILED] Benchmark exited with code $EXIT_CODE"
fi

# ---------------------------------------------------------------
# Upload results to MinIO
# ---------------------------------------------------------------
echo ""
if ! command -v mc &> /dev/null; then
    echo "[UPLOAD] WARNING: mc (MinIO Client) not found. Skipping upload."
    echo "[UPLOAD] Install mc to enable automatic results upload to MinIO."
elif [ ! -f "$RESULTS_FILE" ]; then
    echo "[UPLOAD] WARNING: Results file not found at $RESULTS_FILE. Skipping upload."
else
    echo "[UPLOAD] Uploading results to MinIO..."
    MC_ALIAS="benchmark-minio"
    mc alias set "$MC_ALIAS" "$S3_ENDPOINT_URL" "$S3_ACCESS_KEY" "$S3_SECRET_KEY" --api S3v4 > /dev/null 2>&1

    mc mb --ignore-existing "${MC_ALIAS}/${BENCHMARK_BUCKET}" > /dev/null 2>&1

    RESULTS_BASENAME=$(basename "$RESULTS_FILE")
    if mc cp "$RESULTS_FILE" "${MC_ALIAS}/${BENCHMARK_BUCKET}/${RESULTS_BASENAME}"; then
        echo "[UPLOAD] OK: s3://${BENCHMARK_BUCKET}/${RESULTS_BASENAME}"
    else
        echo "[UPLOAD] WARNING: Upload failed. Results are still saved locally at $RESULTS_FILE"
    fi
fi

exit $EXIT_CODE
