"""Quick test of deploy_reflections login + recommendation flow against sample_1Tb."""
import os
import sys
import requests
import time
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DREMIO_URL = os.getenv("DREMIO_URL", "").rstrip("/")
DREMIO_USERNAME = os.getenv("DREMIO_USERNAME")
DREMIO_PASSWORD = os.getenv("DREMIO_PASSWORD")
NESSIE_SOURCE_NAME = os.getenv("NESSIE_SOURCE_NAME")

# Override to sample dataset for testing
TEST_FOLDER = "sample_1Tb"

print(f"Dremio URL:  {DREMIO_URL}")
print(f"Username:    {DREMIO_USERNAME}")
print(f"Schema:      \"{NESSIE_SOURCE_NAME}\".\"{TEST_FOLDER}\"")

# Step 1: Login
print("\n[1] Logging in...")
res = requests.post(
    f"{DREMIO_URL}/apiv2/login",
    json={"userName": DREMIO_USERNAME, "password": DREMIO_PASSWORD},
)
print(f"  Status: {res.status_code}")
if res.status_code != 200:
    print(f"  Response: {res.text[:300]}")
    sys.exit(1)
token = res.json()["token"]
print(f"  Token: {token[:20]}...")
headers = {"Authorization": f"_dremio{token}", "Content-Type": "application/json"}

# Step 2: Run a simple query (query_96)
query = """select count(*)
from store_sales
    ,household_demographics
    ,time_dim, store
where ss_sold_time_sk = time_dim.t_time_sk
    and ss_hdemo_sk = household_demographics.hd_demo_sk
    and ss_store_sk = s_store_sk
    and time_dim.t_hour = 8
    and time_dim.t_minute >= 30
    and household_demographics.hd_dep_count = 5
    and store.s_store_name = 'ese'
order by count(*)
limit 100"""

print("\n[2] Submitting query_96...")
res = requests.post(
    f"{DREMIO_URL}/api/v3/sql",
    headers=headers,
    json={"sql": query, "context": [NESSIE_SOURCE_NAME, TEST_FOLDER]},
)
print(f"  Status: {res.status_code}")
if res.status_code != 200:
    print(f"  Response: {res.text[:300]}")
    sys.exit(1)
job_id = res.json().get("id")
print(f"  Job ID: {job_id}")

# Step 3: Wait for completion
print("\n[3] Waiting for job to complete...", end="", flush=True)
while True:
    status_res = requests.get(f"{DREMIO_URL}/api/v3/job/{job_id}", headers=headers)
    state = status_res.json().get("jobState")
    if state == "COMPLETED":
        print(f" {state}")
        break
    elif state in ("FAILED", "CANCELED", "INVALID"):
        print(f" {state}")
        print(f"  Error: {status_res.json().get('errorMessage', 'unknown')[:200]}")
        sys.exit(1)
    print(".", end="", flush=True)
    time.sleep(1)

# Step 4: Request recommendations
print("\n[4] Requesting reflection recommendations...")
res = requests.post(
    f"{DREMIO_URL}/api/v3/reflection/recommendations",
    headers=headers,
    json={"jobIds": [job_id]},
)
print(f"  Status: {res.status_code}")
print(f"  Response: {res.text[:500]}")

if res.status_code == 200:
    data = res.json()
    recs = data.get("data", [])
    print(f"\n  Recommendations: {len(recs)}")
    for i, rec in enumerate(recs):
        print(f"\n  --- Recommendation {i+1} ---")
        if "viewRequestBody" in rec:
            print(f"  View: {rec['viewRequestBody'].get('path', 'unknown')}")
        if "reflectionRequestBody" in rec:
            rb = rec["reflectionRequestBody"]
            print(f"  Type: {rb.get('type', 'unknown')}")
            if "dimensionFields" in rb:
                print(f"  Dimensions: {[f['name'] for f in rb['dimensionFields']]}")
            if "measureFields" in rb:
                print(f"  Measures: {[f['name'] for f in rb['measureFields']]}")

    if not recs:
        print("  (No recommendations returned — this is normal for simple queries)")

print("\nTest complete.")
