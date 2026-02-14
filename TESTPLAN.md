# TPC-DS Benchmark — Working Checklist

## Methodology

- **3 runs per phase**, discard the 1st (warm-up), average the remaining 2
- Record **per-query latency** and **total elapsed time** for every run
- Capture Grafana MinIO dashboard for each run

---

## Phase 1: Cold Run Baseline (No Reflections, No Cache)

**Purpose:** Establish raw query engine performance. Every byte read from MinIO over 100 Gbps link.

| Setting | Value |
|---------|-------|
| Mode | `full-noref` |
| Reflections | Disabled |
| Autonomous Reflections | Disabled |
| C3 Cache | Disabled |
| Dataset | `1Tb_512Mb_partition` |
| Pod command | `./benchmark-kit/run_benchmark.sh full-noref` |

**Pre-flight checklist:**
- [ ] Disable Autonomous Reflections
- [ ] Disable C3 local caching: Dremio UI > Sources > "pedros nessie" > Edit > uncheck "Enable local caching when possible"
- [ ] Restart executor pods to clear any existing cached data (OpenShift: scale StatefulSet to 0, then back to 4)
- [ ] Disable any manually created Reflections
- [ ] Confirm Dremio engine "tpcds" is running with 4 executors
- [ ] Verify no other users/workloads running
- [ ] Verify no background jobs (compaction, reflection refresh, metadata refresh)
- [ ] Verify no MinIO healing ops: `mc admin heal --dry-run`

> **Note:** The original test plan specified `ALTER SYSTEM SET "dremio.exec.cache.enabled" = false` but this setting does not exist in Dremio Enterprise v26.0.9. C3 caching is controlled per-source via the UI.

### Run 1a (warm-up — discard, pre-fix baseline)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_512Mb_partition_noref_20260213-172248.csv` |
| Pod start (UTC) | 2026-02-13 17:22:48 |
| Total elapsed | ~2h 45m |
| Queries succeeded | 81 / 99 |
| Queries failed | 18 / 99 (18.2%) |
| Avg query (succeeded) | ~99s |
| Max query | 1,209,674ms (~20min, query_49.sql) |
| Error breakdown | 11 Gandiva cast, 6 divide-by-zero, 1 schema mismatch |
| Status | **Discarded** — 18 query errors fixed, need re-run |

### Run 1b (warm-up — discard, post-fix #1)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_512Mb_partition_noref_20260213-225721.csv` |
| Pod start (UTC) | 2026-02-13 22:57:21 |
| Total elapsed | ~1h 02m |
| Queries succeeded | 95 / 99 |
| Queries failed | 4 / 99 (4.04%) |
| Avg query (succeeded) | 37.6s |
| Max query | 636s (query_36.sql) |
| Error breakdown | 4 Gandiva divide-by-zero in FILTER/PROJECT context |
| Remaining errors | query_39, query_73, query_76, query_79 |
| Status | **Discarded** — 4 remaining errors fixed with cross-multiplication |

### Run 1c (warm-up — discard, unmodified queries)

| Item | Value |
|------|-------|
| JMeter CSV | |
| Pod start (UTC) | |
| Pod end (UTC) | |
| Total elapsed | |
| Queries succeeded | |
| Queries failed | |
| Grafana screenshot | |
| Grafana link | |

### Run 1d (measured)

| Item | Value |
|------|-------|
| JMeter CSV | |
| Pod start (UTC) | |
| Pod end (UTC) | |
| Total elapsed | |
| Queries succeeded | |
| Queries failed | |
| Grafana screenshot | |
| Grafana link | |

### Run 1e (measured)

| Item | Value |
|------|-------|
| JMeter CSV | |
| Pod start (UTC) | |
| Pod end (UTC) | |
| Total elapsed | |
| Queries succeeded | |
| Queries failed | |
| Grafana screenshot | |
| Grafana link | |

### Phase 1 Summary

| Metric | Run 1d | Run 1e | Average |
|--------|--------|--------|---------|
| Total elapsed | | | |
| Queries succeeded | | | |
| Avg per-query (succeeded) | | | |
| Min query | | | |
| Max query | | | |

---

## Phase 2: Warm Run (Cache Enabled, No Reflections)

**Purpose:** Measure the effect of C3 caching.

| Setting | Value |
|---------|-------|
| Mode | `full-noref` |
| Reflections | Disabled |
| C3 Cache | Enabled |
| Dataset | `1Tb_512Mb_partition` |
| Pod command | `./benchmark-kit/run_benchmark.sh full-noref` |

**Pre-flight checklist:**
- [ ] Enable C3 local caching: Dremio UI > Sources > "pedros nessie" > Edit > check "Enable local caching when possible"
- [ ] Reflections still disabled
- [ ] Confirm Dremio engine "tpcds" is running with 4 executors

### Run 2a (cache prime — discard)

| Item | Value |
|------|-------|
| JMeter CSV | |
| Pod start (UTC) | |
| Pod end (UTC) | |
| Total elapsed | |
| Grafana screenshot | |
| Grafana link | |

### Run 2b (measured)

| Item | Value |
|------|-------|
| JMeter CSV | |
| Pod start (UTC) | |
| Pod end (UTC) | |
| Total elapsed | |
| Grafana screenshot | |
| Grafana link | |

### Run 2c (measured)

| Item | Value |
|------|-------|
| JMeter CSV | |
| Pod start (UTC) | |
| Pod end (UTC) | |
| Total elapsed | |
| Grafana screenshot | |
| Grafana link | |

### Phase 2 Summary

| Metric | Run 2b | Run 2c | Average |
|--------|--------|--------|---------|
| Total elapsed | | | |
| Avg per-query | | | |
| Min query | | | |
| Max query | | | |

---

## Phase 3: Reflections Enabled

**Purpose:** Measure impact of Dremio's data optimization features.

| Setting | Value |
|---------|-------|
| Mode | `full-wref` |
| Reflections | Enabled (via deploy_reflections.py or Autonomous) |
| C3 Cache | Enabled |
| Dataset | `1Tb_512Mb_partition` |
| Pod command | `./benchmark-kit/run_benchmark.sh full-wref` |

**Pre-flight checklist:**
- [ ] Enable Autonomous Reflections (if available) or run `deploy_reflections.py`
- [ ] Wait for all reflections to materialize
- [ ] Confirm C3 local caching is enabled on Nessie source (should already be from Phase 2)
- [ ] Confirm Dremio engine "tpcds" is running with 4 executors

### Run 3a (warm-up — discard)

| Item | Value |
|------|-------|
| JMeter CSV | |
| Pod start (UTC) | |
| Pod end (UTC) | |
| Total elapsed | |
| Grafana screenshot | |
| Grafana link | |

### Run 3b (measured)

| Item | Value |
|------|-------|
| JMeter CSV | |
| Pod start (UTC) | |
| Pod end (UTC) | |
| Total elapsed | |
| Grafana screenshot | |
| Grafana link | |

### Run 3c (measured)

| Item | Value |
|------|-------|
| JMeter CSV | |
| Pod start (UTC) | |
| Pod end (UTC) | |
| Total elapsed | |
| Grafana screenshot | |
| Grafana link | |

### Phase 3 Summary

| Metric | Run 3b | Run 3c | Average |
|--------|--------|--------|---------|
| Total elapsed | | | |
| Avg per-query | | | |
| Min query | | | |
| Max query | | | |

---

## Phase 4: Concurrency Testing (future)

**Purpose:** Understand throughput under load.

- Use best config from Phases 1-3
- 5 concurrent users (matches Intel/AWS methodology)
- WLM "High Cost User Queries" queue limits concurrency to 10 — document if adjusted
- Requires modifying JMeter thread group `num_threads` from 1 to 5

---

## Phase 5: Scale-Out (optional, future)

**Purpose:** Validate linear scalability.

- Repeat Phase 1 at different executor counts (2, 3, 4)
- Plot execution time vs. node count

---

## Final Comparison

| Metric | Phase 1 (cold) | Phase 2 (warm) | Phase 3 (reflections) |
|--------|----------------|----------------|-----------------------|
| Total elapsed (avg) | | | |
| Avg per-query (avg) | | | |
| Min query | | | |
| Max query | | | |
| Speedup vs Phase 1 | 1.0x | | |

### Reference Benchmarks

| Source | Config | Result |
|--------|--------|--------|
| Dremio June 2025 "20x Faster" | 8-node m7gd.4xlarge, Autonomous Reflections, cache disabled | 99 queries in 22s |
| Dremio 21.0 (Aug 2025) | m5d.8xlarge / i3.4xlarge | ~30% improvement over prior |
| Intel/AWS white paper | 8/16-node m5dn/m6id, 5 concurrent users, 500 total queries | tabular results |

---

## Completed Runs

### Partial Test (validation) — 2026-02-12

| Item | Value |
|------|-------|
| Mode | `partial` (3 queries) |
| Dataset | `1Tb_512Mb_partition` |
| Result | All 3 queries succeeded |
| query_1.sql | 40.5s |
| query_10.sql | 149.5s |
| query_98.sql | 97.0s |
| Grafana | `results/Grafana/sample_1Tb_partial_20260212-212300.png` |
| Grafana link | http://localhost:3000/public-dashboards/140bb7e2a73f4922b445dd299c22f953 |
| Key observation | MinIO egress ~1.5 GiB/s, storage not bottleneck on sample data |

---

## Query Modifications

**Decision: Use unmodified TPC-DS queries.** All 99 queries run as-is from the standard TPC-DS templates. Queries that fail due to Dremio/Gandiva limitations are recorded as failures and excluded from timing analysis, matching the approach used in published Dremio benchmarks (e.g., `sergeleo/dremio-tpc-ds` which reported 58/99 queries for sf1000).

### Known Dremio v26.0.9 Failure Modes

The following failure modes were identified during Runs 1a and 1b. Rather than modifying queries, we let them fail naturally:

| Failure Mode | Affected Queries | Root Cause |
|-------------|-----------------|------------|
| Gandiva cast error | ~11 queries | Gandiva cannot cast decimal columns compared to integer literals |
| Gandiva divide-by-zero (PROJECT) | query_3, query_10, query_14, query_19, query_21, query_39, query_96 | Division by zero in SELECT expressions; Gandiva does not short-circuit |
| Gandiva divide-by-zero (FILTER) | query_73, query_76, query_79 | Division by zero in WHERE clauses; Gandiva FILTER evaluator evaluates all rows regardless of CASE/NULLIF guards |

### Previous Fix Attempts (reverted)

Runs 1a–1b attempted to fix these failures with query modifications (decimal literal suffixes, NULLIF wrapping, cross-multiplication). These were reverted because:
1. Modifying queries departs from the standard TPC-DS benchmark
2. The reference benchmark (Dremio 4.2.1) also did not run all 99 queries — comparing only successful queries is standard practice
3. Some fixes (cross-multiplication) had minor semantic differences from the original queries

### Iceberg Schema Fix

The `iceberg-kit/tpcds_schema.json` incorrectly named the customer column `c_last_review_date_sk` (with `_sk` suffix). The standard TPC-DS schema uses `c_last_review_date`. This caused `query_75.sql` to fail with a schema mismatch. Fixed by:

1. Correcting `iceberg-kit/tpcds_schema.json`: `c_last_review_date_sk` → `c_last_review_date`
2. Running `ALTER TABLE ... CHANGE COLUMN c_last_review_date_sk c_last_review_date VARCHAR` on all three Nessie folders (`1Tb_512Mb_partition`, `1Tb`, `sample_1Tb`)
3. Restoring `c_last_review_date` in `query_75.sql` SELECT and ORDER BY (no columns removed)

### JMeter Test Plan Changes

| File | Change | Reason |
|------|--------|--------|
| `full_test_plan_noref.jmx` | `on_sample_error` changed from `stopthread` to `continue` | JMeter was aborting after first query failure, preventing all 99 queries from running |
| `full_test_plan_noref.jmx` | `success_only_logging` changed from `true` to `false` | Failed queries were not being recorded in the results CSV |
| `full_test_plan_wref.jmx` | Same two changes as above | Consistency across test plans |

---

## Notes

- **C3 (Columnar Cloud Cache)**: Dremio's executor-level cache. In v26.0.9, controlled per-source via UI (Edit source > "Enable local caching when possible"). The SQL command `ALTER SYSTEM SET "dremio.exec.cache.enabled"` does **not** exist in this version. Restart executor pods after disabling to clear existing cache.
- **Result Cache**: Enterprise feature for identical queries (< 20MB). 99 unique TPC-DS queries won't hit cache.
- **Reflections**: Pre-computed materializations. `deploy_reflections.py` runs all 99 queries and creates Dremio-recommended reflections.
- **Autonomous Reflections**: Dremio auto-creates reflections based on query patterns. May not be available in all editions.
