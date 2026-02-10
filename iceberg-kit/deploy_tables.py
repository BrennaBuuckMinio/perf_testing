import os
import sys
import json
import requests
from dotenv import load_dotenv
import boto3
import urllib.parse
import time  # Ensure 'time' is imported for sleep functionality
import argparse  # Add argparse for command-line arguments

# Disable output buffering for real-time logging in containers/Kubernetes
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Load environment variables from .env file
load_dotenv()

# Retrieve credentials and configuration from environment variables
DREMIO_USERNAME = os.getenv("DREMIO_USERNAME")
DREMIO_PASSWORD = os.getenv("DREMIO_PASSWORD")
DREMIO_URL = os.getenv("DREMIO_URL")


S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")

ICEBERG_BUCKET_NAME = os.getenv("ICEBERG_BUCKET_NAME")
ICEBERG_FOLDER_NAME = os.getenv("ICEBERG_FOLDER_NAME")
ICEBERG_SUBFOLDER = os.getenv("ICEBERG_SUBFOLDER")  # Default to empty if not set
S3_OBJECT_STORE = os.getenv("S3_BUCKET_NAME")
S3_FOLDER_NAME = os.getenv("S3_FOLDER_NAME")

# Dremio source names
DREMIO_SOURCE_NAME = os.getenv("DREMIO_SOURCE_NAME")  # e.g., "tpcds"
NESSIE_SOURCE_NAME = os.getenv("NESSIE_SOURCE_NAME")  # e.g., "pedros nessie"


if not DREMIO_USERNAME or not DREMIO_PASSWORD or not DREMIO_URL or not ICEBERG_BUCKET_NAME:
    raise ValueError("DREMIO_USERNAME, DREMIO_PASSWORD, DREMIO_URL, and DREMIO_SOURCE_NAME must be set in the environment variables.")

if not S3_BUCKET_NAME or not S3_ENDPOINT_URL or not S3_ACCESS_KEY or not S3_SECRET_KEY:
    raise ValueError("S3_BUCKET_NAME, S3_ENDPOINT_URL, S3_ACCESS_KEY, and S3_SECRET_KEY must be set in the environment variables.")

if not ICEBERG_BUCKET_NAME or not S3_OBJECT_STORE:
    raise ValueError("ICEBERG_BUCKET_NAME and S3_OBJECT_STORE must be set in the environment variables.")

if not DREMIO_SOURCE_NAME or not NESSIE_SOURCE_NAME or not S3_FOLDER_NAME:
    raise ValueError("DREMIO_SOURCE_NAME, NESSIE_SOURCE_NAME, and S3_FOLDER_NAME must be set in the environment variables.")

# Initialize S3 client
s3 = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY
)

def get_auth_header():
    """Get authentication header for Dremio API calls"""
    auth_payload = {
        "userName": DREMIO_USERNAME,
        "password": DREMIO_PASSWORD
    }
    try:
        response = requests.post(f"{DREMIO_URL}/apiv2/login", json=auth_payload)
        response.raise_for_status()
        token = response.json()["token"]
        return {"Authorization": f"_dremio{token}", "Content-Type": "application/json"}
    except requests.exceptions.RequestException as e:
        print(f"Authentication failed: {e}")
        return None

def get_catalog_entity_by_path(path_list):
    """Get catalog entity details by path (e.g., ['tpcds', 'sample_1Tb', 'reason'])"""
    headers = get_auth_header()
    if not headers:
        return None

    # URL encode the path
    encoded_path = "/".join(urllib.parse.quote(p, safe='') for p in path_list)

    try:
        response = requests.get(
            f"{DREMIO_URL}/api/v3/catalog/by-path/{encoded_path}",
            headers=headers
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to get catalog entity: {e}")
        return None


def promote_folder(source_name, folder_path, table_name):
    """
    Promote a folder to a Parquet dataset in Dremio.

    Args:
        source_name: Name of the S3 source (e.g., 'tpcds')
        folder_path: Path within the source (e.g., 'sample_1Tb')
        table_name: Name of the table/folder to promote (e.g., 'reason')

    Returns:
        True if promotion succeeded or already promoted, False otherwise
    """
    print(f"[PROMOTE] Starting promotion check for table '{table_name}'...")

    headers = get_auth_header()
    if not headers:
        print(f"[PROMOTE] ERROR: Failed to authenticate for table '{table_name}'")
        return False

    path_list = [source_name, folder_path, table_name]

    # First check if it's already promoted (is a dataset)
    print(f"[PROMOTE] Checking if '{table_name}' is already promoted...")
    entity = get_catalog_entity_by_path(path_list)
    if entity:
        entity_type = entity.get('entityType')
        if entity_type == 'dataset':
            print(f"[PROMOTE] '{table_name}' is already promoted as a dataset - skipping promotion")
            return True
        elif entity_type == 'folder':
            # Need to promote it
            entity_id = entity.get('id')
            print(f"[PROMOTE] '{table_name}' is a folder - will promote to dataset")
        else:
            print(f"[PROMOTE] ERROR: Unexpected entity type for '{table_name}': {entity_type}")
            return False
    else:
        print(f"[PROMOTE] ERROR: Could not find '{table_name}' in catalog. Make sure the folder exists.")
        return False

    # Promote the folder to a dataset
    # The API requires us to PUT to the catalog endpoint with format settings
    promote_payload = {
        "entityType": "dataset",
        "id": entity_id,
        "path": path_list,
        "type": "PHYSICAL_DATASET",
        "format": {
            "type": "Parquet"
        }
    }

    try:
        print(f"[PROMOTE] Promoting folder '{table_name}' to Parquet dataset...")
        # URL-encode the entity_id since it contains special characters like ':'
        encoded_entity_id = urllib.parse.quote(entity_id, safe='')
        response = requests.post(
            f"{DREMIO_URL}/api/v3/catalog/{encoded_entity_id}",
            headers=headers,
            json=promote_payload
        )
        response.raise_for_status()
        print(f"[PROMOTE] SUCCESS: Done promoting '{table_name}' to Parquet dataset")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[PROMOTE] FAILED: Could not promote folder '{table_name}': {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[PROMOTE] Error response: {e.response.text}")
        return False


def execute_query(query):
    """Execute a SQL query in Dremio and wait for results"""
    headers = get_auth_header()
    if not headers:
        return False

    # Step 1: Submit the query
    submit_payload = {
        "sql": query
    }

    try:
        print(f"Submitting SQL query: {query}")
        response = requests.post(
            f"{DREMIO_URL}/api/v3/sql",
            headers=headers,
            json=submit_payload
        )
        response.raise_for_status()
        job_id = response.json().get('id')

        if not job_id:
            print("No job ID returned from query submission")
            return False

        # Step 2: Poll for query status
        while True:
            status_response = requests.get(
                f"{DREMIO_URL}/api/v3/job/{job_id}",
                headers=headers
            )
            status_response.raise_for_status()
            status = status_response.json()

            if status.get('jobState') == 'COMPLETED':
                print("Query completed successfully")
                return True
            elif status.get('jobState') in ['FAILED', 'CANCELED', 'INVALID']:
                print(f"Query failed with state: {status.get('jobState')}")
                print(f"Error: {status.get('errorMessage')}")
                return False

            time.sleep(1)  # Wait before polling again

    except requests.exceptions.RequestException as e:
        print(f"Failed to execute query: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error response: {e.response.text}")
        return False

def load_tpcds_schema():
    """Load TPC-DS schema definitions from tpcds_schema.json"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    schema_file = os.path.join(script_dir, "tpcds_schema.json")

    if not os.path.exists(schema_file):
        print(f"[SCHEMA] Warning: {schema_file} not found. Using generic column names.")
        return None

    with open(schema_file, "r") as f:
        return json.load(f)


def build_select_with_schema(table_name, schema):
    """
    Build a SELECT statement that renames _c0, _c1, etc. to proper TPC-DS column names.

    Args:
        table_name: Name of the table
        schema: TPC-DS schema dictionary

    Returns:
        SELECT clause with column mappings, or None if schema not found
    """
    if not schema or table_name not in schema.get("tables", {}):
        return None

    table_schema = schema["tables"][table_name]
    columns = table_schema.get("columns", [])

    select_parts = []

    # Map _c0, _c1, etc. to proper column names
    for i, col_name in enumerate(columns):
        select_parts.append(f"_c{i} as {col_name}")

    return ", ".join(select_parts)


def process_table(table_name, partition_column=None, localsort_column=None, schema=None):
    """Query the object and create the Iceberg table with proper TPC-DS schema."""
    # Step 1: Promote the folder to a Parquet dataset (if not already)
    print(f"\n{'='*60}")
    print(f"Processing table: {table_name}")
    print(f"{'='*60}")

    if not promote_folder(DREMIO_SOURCE_NAME, S3_FOLDER_NAME, table_name):
        print(f"Warning: Could not promote '{table_name}', attempting to query anyway...")

    # Step 2: Query the object with LIMIT 1 to verify it's accessible
    query = f"""
    SELECT * FROM {DREMIO_SOURCE_NAME}."{S3_FOLDER_NAME}"."{table_name}" LIMIT 1
    """
    print(f"Verifying dataset accessibility for: {table_name}")
    if not execute_query(query):
        print(f"Failed to verify dataset '{table_name}', skipping Iceberg table creation")
        return

    # Step 3: Check if Iceberg table already exists
    iceberg_path = [NESSIE_SOURCE_NAME, S3_FOLDER_NAME, table_name]
    existing_table = get_catalog_entity_by_path(iceberg_path)
    if existing_table and existing_table.get('entityType') == 'dataset':
        print(f"[ICEBERG] Table '{table_name}' already exists in Nessie catalog - skipping creation")
        return

    # Step 4: Build SELECT statement with proper column names
    select_clause = build_select_with_schema(table_name, schema)

    if select_clause:
        print(f"[ICEBERG] Using TPC-DS schema for column mapping")
    else:
        # Fallback to SELECT * if no schema mapping
        select_clause = "*"
        print(f"[ICEBERG] No schema mapping found, using SELECT *")

    # Step 5: Create the Iceberg table
    print(f"[ICEBERG] Starting Iceberg table creation for '{table_name}'...")

    if partition_column and schema:
        # Use partitioning with proper column names
        localsort_clause = f" LOCALSORT BY ({localsort_column})" if localsort_column else ""
        create_query = f"""
        CREATE TABLE "{NESSIE_SOURCE_NAME}"."{S3_FOLDER_NAME}"."{table_name}"
        PARTITION BY ({partition_column}){localsort_clause} AS
        SELECT {select_clause}
        FROM {DREMIO_SOURCE_NAME}."{S3_FOLDER_NAME}"."{table_name}"
        """
        print(f"[ICEBERG] Creating partitioned table (partition_by={partition_column}, localsort_by={localsort_column})")
    else:
        create_query = f"""
        CREATE TABLE "{NESSIE_SOURCE_NAME}"."{S3_FOLDER_NAME}"."{table_name}" AS
        SELECT {select_clause}
        FROM {DREMIO_SOURCE_NAME}."{S3_FOLDER_NAME}"."{table_name}"
        """
        print(f"[ICEBERG] Creating non-partitioned table")

    if execute_query(create_query):
        print(f"[ICEBERG] SUCCESS: Done creating Iceberg table '{table_name}'")
    else:
        print(f"[ICEBERG] FAILED: Could not create Iceberg table '{table_name}'")

def promote_all_tables(tables):
    """Promote all folders to Parquet datasets without creating Iceberg tables."""
    print("\n" + "="*60)
    print("PROMOTING ALL FOLDERS TO PARQUET DATASETS")
    print("="*60)

    all_tables = list(tables["partitioned_tables"].keys()) + tables["non_partitioned_tables"]
    success_count = 0
    fail_count = 0

    for table_name in all_tables:
        if promote_folder(DREMIO_SOURCE_NAME, S3_FOLDER_NAME, table_name):
            success_count += 1
        else:
            fail_count += 1

    print(f"\n{'='*60}")
    print(f"PROMOTION COMPLETE: {success_count} succeeded, {fail_count} failed")
    print(f"{'='*60}")
    return fail_count == 0


def main():
    parser = argparse.ArgumentParser(description="Deploy Iceberg tables from S3 objects")
    parser.add_argument("--table", help="Specific table name to process (without fetching the list)")
    parser.add_argument("--promote-only", action="store_true", help="Only promote folders to datasets, don't create Iceberg tables")
    args = parser.parse_args()

    # Load TPC-DS schema for column name mapping
    schema = load_tpcds_schema()
    if schema:
        print(f"[SCHEMA] Loaded TPC-DS schema with {len(schema.get('tables', {}))} table definitions")
    else:
        print("[SCHEMA] No schema loaded - tables will have generic column names (_c0, _c1, etc.)")

    if args.table:
        # Process only the specified table
        table_name = args.table
        print(f"Processing single table: {table_name}")

        # Load tables.json to check if the table is partitioned or not
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tables_file = os.path.join(script_dir, "tables.json")
        partition_column = None
        localsort_column = None

        if os.path.exists(tables_file):
            with open(tables_file, "r") as f:
                tables = json.load(f)
                if table_name in tables.get("partitioned_tables", {}):
                    config = tables["partitioned_tables"][table_name]
                    partition_column = config.get("partition_by")
                    localsort_column = config.get("localsort_by")
                    print(f"Table is partitioned by: {partition_column}, localsort by: {localsort_column}")
                elif table_name in tables.get("non_partitioned_tables", []):
                    print(f"Table is non-partitioned")
                else:
                    print(f"Table '{table_name}' not found in tables.json, treating as non-partitioned")

        process_table(table_name, partition_column=partition_column, localsort_column=localsort_column,
                      schema=schema)
    else:
        # Load tables.json from the same directory as this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tables_file = os.path.join(script_dir, "tables.json")
        if not os.path.exists(tables_file):
            print(f"Error: {tables_file} not found.")
            return

        try:
            with open(tables_file, "r") as f:
                tables = json.load(f)
                # Debug: Print the contents of tables.json
                print("Contents of tables.json:")
                print(json.dumps(tables, indent=4))
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse {tables_file}. Ensure it contains valid JSON. {e}")
            return

        # If --promote-only flag is set, just promote all folders and exit
        if args.promote_only:
            promote_all_tables(tables)
            return

        # Process partitioned tables
        for table_name, config in tables["partitioned_tables"].items():
            # Debug: Print table_name and config to verify structure
            print(f"Processing partitioned table: {table_name}")
            print(f"Config for {table_name}: {config}")

            # Ensure config contains the expected keys
            if "partition_by" not in config or "localsort_by" not in config:
                print(f"Error: Missing 'partition_by' or 'localsort_by' in config for table {table_name}")
                continue

            partition_column = config["partition_by"]
            localsort_column = config["localsort_by"]
            process_table(table_name, partition_column, localsort_column, schema=schema)

        # Process non-partitioned tables
        for table_name in tables["non_partitioned_tables"]:
            process_table(table_name, schema=schema)

if __name__ == "__main__":
    main()
