"""Toggle reflections on/off by type (RAW or AGGREGATE) for a given dataset folder."""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DREMIO_URL = os.getenv("DREMIO_URL", "").rstrip("/")
DREMIO_USERNAME = os.getenv("DREMIO_USERNAME")
DREMIO_PASSWORD = os.getenv("DREMIO_PASSWORD")
NESSIE_SOURCE_NAME = os.getenv("NESSIE_SOURCE_NAME")
ICEBERG_FOLDER_NAME = os.getenv("ICEBERG_FOLDER_NAME")


def login():
    res = requests.post(
        f"{DREMIO_URL}/apiv2/login",
        json={"userName": DREMIO_USERNAME, "password": DREMIO_PASSWORD},
    )
    res.raise_for_status()
    return res.json()["token"]


def get_headers(token):
    return {"Authorization": f"_dremio{token}", "Content-Type": "application/json"}


def get_all_reflections(headers):
    """Get all reflections via the catalog API."""
    reflections = []
    # List reflections - there's no single "list all" endpoint, so we go through datasets
    # Instead, use the undocumented reflections list endpoint
    res = requests.get(f"{DREMIO_URL}/api/v3/reflection", headers=headers)
    if res.status_code == 200:
        return res.json().get("data", [])
    # Fallback: try alternate format
    return []


def toggle_reflection(headers, ref, enabled):
    """Enable or disable a specific reflection by sending the full object."""
    ref_id = ref["id"]
    # Copy the reflection and update enabled
    payload = dict(ref)
    payload["enabled"] = enabled
    res = requests.put(
        f"{DREMIO_URL}/api/v3/reflection/{ref_id}",
        headers=headers,
        json=payload,
    )
    if res.status_code not in (200, 201):
        # Debug: print error
        print(f"    API error: {res.status_code} - {res.text[:150]}")
    return res.status_code in (200, 201)


def main():
    if len(sys.argv) < 3:
        print("Usage: toggle_reflections.py <RAW|AGGREGATE> <enable|disable>")
        print("  Environment: ICEBERG_FOLDER_NAME controls which dataset folder")
        sys.exit(1)

    ref_type = sys.argv[1].upper()
    action = sys.argv[2].lower()

    if ref_type not in ("RAW", "AGGREGATE"):
        print(f"Invalid type: {ref_type}. Use RAW or AGGREGATE.")
        sys.exit(1)
    if action not in ("enable", "disable"):
        print(f"Invalid action: {action}. Use enable or disable.")
        sys.exit(1)

    enabled = action == "enable"

    print(f"{'='*60}")
    print(f"  Toggle Reflections: {action.upper()} all {ref_type}")
    print(f"  Dremio:  {DREMIO_URL}")
    print(f"  Schema:  \"{NESSIE_SOURCE_NAME}\".\"{ICEBERG_FOLDER_NAME}\"")
    print(f"{'='*60}")

    token = login()
    headers = get_headers(token)
    print("[AUTH] Login successful.")

    all_refs = get_all_reflections(headers)
    print(f"\n[REFLECTIONS] Found {len(all_refs)} total reflections.")

    # Filter by type
    matching = [r for r in all_refs if r.get("type") == ref_type]
    print(f"  {ref_type} reflections: {len(matching)}")

    # Further filter: only reflections whose dataset path contains our folder
    # Get dataset info for each reflection to check path
    toggled = 0
    skipped = 0

    for ref in matching:
        dataset_id = ref.get("datasetId", "")
        ref_id = ref.get("id", "")
        ref_name = ref.get("name", "unknown")
        ref_enabled = ref.get("enabled", False)
        tag = ref.get("tag", "")

        # Check if this reflection's dataset belongs to our folder
        # Get dataset path
        ds_res = requests.get(
            f"{DREMIO_URL}/api/v3/catalog/{dataset_id}",
            headers=headers,
        )
        if ds_res.status_code != 200:
            continue

        ds = ds_res.json()
        path = ds.get("path", [])
        path_str = ".".join(path)

        if ICEBERG_FOLDER_NAME not in path_str:
            continue

        if ref_enabled == enabled:
            print(f"  {ref_name} — already {'enabled' if enabled else 'disabled'}")
            skipped += 1
            continue

        if toggle_reflection(headers, ref, enabled):
            print(f"  {ref_name} — {'enabled' if enabled else 'disabled'}")
            toggled += 1
        else:
            print(f"  {ref_name} — FAILED to toggle")

    print(f"\n{'='*60}")
    print(f"  COMPLETE")
    print(f"  Toggled: {toggled}")
    print(f"  Already in desired state: {skipped}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
