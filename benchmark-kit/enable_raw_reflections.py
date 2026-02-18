"""Enable Raw Reflections on all TPC-DS tables, and create the 'recommended_view' space
for aggregate reflection recommendations."""
import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DREMIO_URL = os.getenv("DREMIO_URL", "").rstrip("/")
DREMIO_USERNAME = os.getenv("DREMIO_USERNAME")
DREMIO_PASSWORD = os.getenv("DREMIO_PASSWORD")
NESSIE_SOURCE_NAME = os.getenv("NESSIE_SOURCE_NAME")
ICEBERG_FOLDER_NAME = os.getenv("ICEBERG_FOLDER_NAME")

# TPC-DS tables (all 24)
TPCDS_TABLES = [
    "call_center", "catalog_page", "catalog_returns", "catalog_sales",
    "customer", "customer_address", "customer_demographics", "date_dim",
    "household_demographics", "income_band", "inventory", "item",
    "promotion", "reason", "ship_mode", "store", "store_returns",
    "store_sales", "time_dim", "warehouse", "web_page", "web_returns",
    "web_sales", "web_site",
]


def login():
    res = requests.post(
        f"{DREMIO_URL}/apiv2/login",
        json={"userName": DREMIO_USERNAME, "password": DREMIO_PASSWORD},
    )
    res.raise_for_status()
    return res.json()["token"]


def get_headers(token):
    return {"Authorization": f"_dremio{token}", "Content-Type": "application/json"}


def create_space(headers, space_name):
    """Create a Dremio space if it doesn't exist."""
    print(f"\n[SPACE] Creating space '{space_name}'...")
    # Check if it exists first
    res = requests.get(
        f"{DREMIO_URL}/api/v3/catalog/by-path/{space_name}",
        headers=headers,
    )
    if res.status_code == 200:
        print(f"  Space '{space_name}' already exists.")
        return True

    res = requests.post(
        f"{DREMIO_URL}/api/v3/catalog",
        headers=headers,
        json={
            "entityType": "space",
            "name": space_name,
        },
    )
    if res.status_code in (200, 201):
        print(f"  Space '{space_name}' created.")
        return True
    else:
        print(f"  Failed to create space: {res.status_code} - {res.text[:200]}")
        return False


def get_dataset_id(headers, table_name):
    """Get the catalog ID for a table."""
    path = f"{NESSIE_SOURCE_NAME}/{ICEBERG_FOLDER_NAME}/{table_name}"
    res = requests.get(
        f"{DREMIO_URL}/api/v3/catalog/by-path/{path}",
        headers=headers,
    )
    if res.status_code == 200:
        return res.json().get("id")
    return None


def enable_raw_reflection(headers, dataset_id, table_name):
    """Enable raw reflection on a dataset."""
    # Get current reflections
    res = requests.get(
        f"{DREMIO_URL}/api/v3/dataset/{dataset_id}/reflection",
        headers=headers,
    )

    if res.status_code != 200:
        # Try alternate endpoint
        res = requests.get(
            f"{DREMIO_URL}/api/v3/reflection?datasetId={dataset_id}",
            headers=headers,
        )

    # Check if raw reflection already exists
    if res.status_code == 200:
        existing = res.json().get("data", [])
        for ref in existing:
            if ref.get("type") == "RAW":
                print(f"  Raw reflection already exists (id: {ref['id']})")
                return True

    # Get dataset details to know the fields
    ds_res = requests.get(
        f"{DREMIO_URL}/api/v3/catalog/{dataset_id}",
        headers=headers,
    )
    if ds_res.status_code != 200:
        print(f"  Could not get dataset details: {ds_res.status_code}")
        return False

    ds = ds_res.json()
    fields = ds.get("fields", [])
    if not fields:
        print(f"  No fields found for {table_name}")
        return False

    # Build display fields list
    display_fields = [{"name": f["name"]} for f in fields]

    # Create raw reflection
    payload = {
        "type": "RAW",
        "name": f"raw_{table_name}",
        "datasetId": dataset_id,
        "enabled": True,
        "displayFields": display_fields,
    }

    res = requests.post(
        f"{DREMIO_URL}/api/v3/reflection",
        headers=headers,
        json=payload,
    )
    if res.status_code in (200, 201):
        ref_id = res.json().get("id", "unknown")
        print(f"  Raw reflection created (id: {ref_id})")
        return True
    else:
        print(f"  Failed: {res.status_code} - {res.text[:200]}")
        return False


def main():
    print(f"{'='*60}")
    print(f"  Enable Raw Reflections + Create recommended_view Space")
    print(f"  Dremio:  {DREMIO_URL}")
    print(f"  Schema:  \"{NESSIE_SOURCE_NAME}\".\"{ICEBERG_FOLDER_NAME}\"")
    print(f"  Tables:  {len(TPCDS_TABLES)}")
    print(f"{'='*60}")

    token = login()
    headers = get_headers(token)
    print("[AUTH] Login successful.")

    # Create recommended_view space
    create_space(headers, "recommended_view")

    # Enable raw reflections on all tables
    print(f"\n[RAW REFLECTIONS] Enabling on {len(TPCDS_TABLES)} tables...\n")
    created = 0
    failed = 0

    for table in TPCDS_TABLES:
        print(f"  {table}...", end=" ", flush=True)
        dataset_id = get_dataset_id(headers, table)
        if not dataset_id:
            print(f"NOT FOUND")
            failed += 1
            continue

        if enable_raw_reflection(headers, dataset_id, table):
            created += 1
        else:
            failed += 1

    print(f"\n{'='*60}")
    print(f"  COMPLETE")
    print(f"  Raw reflections enabled: {created}/{len(TPCDS_TABLES)}")
    print(f"  Failed: {failed}/{len(TPCDS_TABLES)}")
    print(f"{'='*60}")
    print(f"\nReflections will materialize in the background.")
    print(f"Check Dremio Jobs page for reflection refresh jobs.")


if __name__ == "__main__":
    main()
