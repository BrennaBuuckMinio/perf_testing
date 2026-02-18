import os
import requests
import time
import glob
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DREMIO_URL = os.getenv("DREMIO_URL", "").rstrip("/")
DREMIO_USERNAME = os.getenv("DREMIO_USERNAME")
DREMIO_PASSWORD = os.getenv("DREMIO_PASSWORD")
NESSIE_SOURCE_NAME = os.getenv("NESSIE_SOURCE_NAME")
ICEBERG_FOLDER_NAME = os.getenv("ICEBERG_FOLDER_NAME")

if not all([DREMIO_URL, DREMIO_USERNAME, DREMIO_PASSWORD, NESSIE_SOURCE_NAME, ICEBERG_FOLDER_NAME]):
    raise ValueError(
        "Required env vars: DREMIO_URL, DREMIO_USERNAME, DREMIO_PASSWORD, "
        "NESSIE_SOURCE_NAME, ICEBERG_FOLDER_NAME"
    )

SESSION_TOKEN = None


def login():
    """Authenticate with username/password and get a session token."""
    global SESSION_TOKEN
    print(f"[AUTH] Logging in as {DREMIO_USERNAME} to {DREMIO_URL}...")
    res = requests.post(
        f"{DREMIO_URL}/apiv2/login",
        json={"userName": DREMIO_USERNAME, "password": DREMIO_PASSWORD},
    )
    res.raise_for_status()
    SESSION_TOKEN = res.json()["token"]
    print("[AUTH] Login successful.")


def get_auth_header():
    """Return headers with session token."""
    if not SESSION_TOKEN:
        login()
    return {
        "Authorization": f"_dremio{SESSION_TOKEN}",
        "Content-Type": "application/json",
    }


def execute_query(query):
    """Execute a SQL query in Dremio and wait for completion. Returns job_id or None."""
    headers = get_auth_header()
    context = [NESSIE_SOURCE_NAME, ICEBERG_FOLDER_NAME]

    try:
        res = requests.post(
            f"{DREMIO_URL}/api/v3/sql",
            headers=headers,
            json={"sql": query, "context": context},
        )
        res.raise_for_status()
        job_id = res.json().get("id")
        if not job_id:
            print("  No job ID returned.")
            return None
    except requests.RequestException as e:
        print(f"  Submit failed: {e}")
        return None

    # Poll for completion
    while True:
        try:
            status_res = requests.get(
                f"{DREMIO_URL}/api/v3/job/{job_id}", headers=headers
            )
            state = status_res.json().get("jobState")
        except Exception:
            time.sleep(2)
            continue

        if state == "COMPLETED":
            return job_id
        elif state in ("FAILED", "CANCELED", "INVALID"):
            err = status_res.json().get("errorMessage", "unknown error")
            print(f"  Query failed ({state}): {err[:120]}")
            return None
        time.sleep(1)


def request_recommendations(job_id):
    """Ask Dremio for reflection recommendations for a completed job."""
    headers = get_auth_header()
    try:
        res = requests.post(
            f"{DREMIO_URL}/api/v3/reflection/recommendations",
            headers=headers,
            json={"jobIds": [job_id]},
        )
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        print(f"  Recommendations request failed: {e}")
        return None


def create_reflection_from_recommendation(recommendation):
    """Create a view and reflection from a Dremio recommendation."""
    headers = get_auth_header()

    # Create view
    view_payload = recommendation["viewRequestBody"]
    try:
        view_res = requests.post(
            f"{DREMIO_URL}/api/v3/catalog", headers=headers, json=view_payload
        )
        view_res.raise_for_status()
        view_id = view_res.json()["id"]
    except requests.RequestException as e:
        print(f"  View creation failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"  Response: {e.response.text[:200]}")
        return False

    # Create reflection
    reflection_payload = recommendation["reflectionRequestBody"]
    reflection_payload["datasetId"] = view_id
    try:
        ref_res = requests.post(
            f"{DREMIO_URL}/api/v3/reflection",
            headers=headers,
            json=reflection_payload,
        )
        ref_res.raise_for_status()
        print(f"  Reflection created for view {view_id}")
        return True
    except requests.RequestException as e:
        print(f"  Reflection creation failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"  Response: {e.response.text[:200]}")
        return False


def process_queries():
    """Run all 99 TPC-DS queries and create recommended reflections."""
    queries_dir = os.path.join(os.path.dirname(__file__), "queries")
    query_files = sorted(glob.glob(os.path.join(queries_dir, "query_*.sql")))

    if not query_files:
        print(f"No query files found in {queries_dir}")
        return

    print(f"\n{'='*60}")
    print(f"  Deploy Reflections")
    print(f"  Dremio:  {DREMIO_URL}")
    print(f"  Schema:  \"{NESSIE_SOURCE_NAME}\".\"{ICEBERG_FOLDER_NAME}\"")
    print(f"  Queries: {len(query_files)}")
    print(f"{'='*60}\n")

    login()

    total_reflections = 0
    succeeded = 0
    failed = 0

    for i, qpath in enumerate(query_files, 1):
        qname = os.path.basename(qpath)
        with open(qpath, "r") as f:
            query = f.read().strip()

        print(f"[{i:2d}/{len(query_files)}] {qname}...", end=" ", flush=True)

        job_id = execute_query(query)
        if not job_id:
            failed += 1
            continue

        succeeded += 1
        recs = request_recommendations(job_id)
        if recs and "data" in recs and recs["data"]:
            count = len(recs["data"])
            print(f"OK ({count} recommendation{'s' if count > 1 else ''})")
            for rec in recs["data"]:
                if create_reflection_from_recommendation(rec):
                    total_reflections += 1
        else:
            print("OK (no recommendations)")

    print(f"\n{'='*60}")
    print(f"  COMPLETE")
    print(f"  Queries succeeded: {succeeded}/{len(query_files)}")
    print(f"  Queries failed:    {failed}/{len(query_files)}")
    print(f"  Reflections created: {total_reflections}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    process_queries()
