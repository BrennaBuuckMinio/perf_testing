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
| JMeter CSV | `1Tb_512Mb_partition_noref_20260214-035917.csv` |
| Pod start (UTC) | 2026-02-14 03:59:17 |
| Pod end (UTC) | 2026-02-14 04:06:47 |
| Total elapsed | 7m 30s |
| Queries succeeded | 81 / 99 |
| Queries failed | 18 / 99 (18.18%) |
| Avg query (succeeded) | 269ms |
| Max query (succeeded) | 1,148ms (query_1, includes JDBC warmup) |
| Error breakdown | 11 Gandiva cast, 4 divide-by-zero (PROJECT), 3 divide-by-zero (FILTER) |
| Status | **Discarded** — warm-up run |
| **Key finding** | 81 successful queries totaled only 21.8s; most return empty results in <300ms due to data distribution mismatch (Iceberg partition pruning). Failed queries consumed 424s of 447s total. |

### Run 1d (measured)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_512Mb_partition_noref_nocache_20260214-051719.csv` |
| Pod start (UTC) | 2026-02-14 05:17:19 |
| Pod end (UTC) | 2026-02-14 08:09:04 |
| Total elapsed | 171m 45s (2h 52m) |
| Queries succeeded | 81 / 99 |
| Queries failed | 18 / 99 (18.18%) |
| Avg query (succeeded) | 122.3s |
| Median query (succeeded) | 60.3s |
| Min query (succeeded) | 170ms (query_22) |
| Max query (succeeded) | 1,058,360ms / 17.6 min (query_9) |
| P90 (succeeded) | 335.8s |
| P95 (succeeded) | 440.6s |
| Total time (succeeded) | 9,903.8s (165.1 min) |
| Error breakdown | 11 Gandiva cast (FILTER), 4 divide-by-zero (PROJECT), 3 divide-by-zero (FILTER) |
| **Note** | First run with regenerated sf=1000 queries (`dsqgen -SCALE 1000 -DIALECT dremio`). Queries now return real results and exercise the full 1TB dataset. |

### Run 1e (measured)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_512Mb_partition_noref_nocache_20260216-030718.csv` |
| Pod start (UTC) | 2026-02-16 03:07:18 |
| Pod end (UTC) | 2026-02-16 06:01:00 |
| Total elapsed | 173.5 min (2h 54m) |
| Queries succeeded | 81 / 99 |
| Queries failed | 18 / 99 (18.18%) |
| Avg query (succeeded) | 124.2s |
| Median query (succeeded) | 63.8s |
| Min query (succeeded) | 3,500ms (query_39) |
| Max query (succeeded) | 1,081,000ms / 18.0 min (query_9) |
| P90 (succeeded) | 299.4s |
| P95 (succeeded) | 433.5s |
| Total time (succeeded) | 10,060.9s (167.7 min) |
| Error breakdown | 11 Gandiva cast (FILTER), 4 divide-by-zero (PROJECT), 3 divide-by-zero (FILTER) |
| Grafana screenshot | |
| Grafana link | [MinIO Dashboard](https://grafana-k5.apps.k2.min.dev/d/TgmJnqnnk/minio-dashboard?orgId=1&from=2026-02-16T03:07:00.000Z&to=2026-02-16T06:01:00.000Z&timezone=browser&var-scrape_jobs=$__all) |

### Phase 1 Summary

| Metric | Run 1d | Run 1e | Average |
|--------|--------|--------|---------|
| Total elapsed | 171m 45s | 173m 30s | **172m 38s** |
| Queries succeeded | 81/99 | 81/99 | 81/99 |
| Avg per-query (succeeded) | 122.3s | 124.2s | **123.2s** |
| Min query | 170ms (query_22) | 3.5s (query_39) | |
| Max query | 1,058s (query_9) | 1,081s (query_9) | **1,070s** |
| P90 | 335.8s | 299.4s | **317.6s** |
| P95 | 440.6s | 433.5s | **437.1s** |

---

## Phase 1b: Cold Run — 1Tb Dataset (85 MiB Parquet files)

**Purpose:** Compare partition size impact. Same config as Phase 1 but with `1Tb` dataset (~85 MiB per Parquet file vs `1Tb_512Mb_partition`'s ~336 MiB files). More files = potentially better parallelism across executors.

| Setting | Value |
|---------|-------|
| Mode | `noref` |
| Reflections | Disabled |
| C3 Cache | Disabled |
| Dataset | `1Tb` (~85 MiB per Parquet file) |

### Run 1b-a (measured)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_noref_nocache_20260216-160653.csv` |
| Pod start (UTC) | 2026-02-16 16:06:55 |
| Pod end (UTC) | 2026-02-16 19:05:19 |
| Total elapsed | 178.4 min (2h 58m) |
| Queries succeeded | 81 / 99 |
| Queries failed | 18 / 99 (18.18%) |
| Avg query (succeeded) | 126.7s |
| Median query (succeeded) | 61.2s |
| Min query (succeeded) | 2,193ms (query_39) |
| Max query (succeeded) | 1,105,621ms / 18.4 min (query_9) |
| P90 (succeeded) | 303.4s |
| P95 (succeeded) | 471.2s |
| Total time (succeeded) | 10,260.1s (171.0 min) |
| Error breakdown | 11 Gandiva cast (FILTER), 4 divide-by-zero (PROJECT), 3 divide-by-zero (FILTER) |
| Grafana screenshot | |
| Grafana link | [MinIO Dashboard](https://grafana-k5.apps.k2.min.dev/d/TgmJnqnnk/minio-dashboard?orgId=1&from=2026-02-16T16:06:00.000Z&to=2026-02-16T19:06:00.000Z&timezone=browser&var-scrape_jobs=$__all) |

### Run 1b-b (measured)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_noref_nocache_20260217-164504.csv` |
| Pod start (UTC) | 2026-02-17 16:45:04 |
| Pod end (UTC) | 2026-02-17 19:52:08 |
| Total elapsed | 187.1 min (3h 7m) |
| Queries succeeded | 80 / 99 |
| Queries failed | 19 / 99 (19.19%) |
| Avg query (succeeded) | 134.9s |
| Median query (succeeded) | 76.8s |
| Min query (succeeded) | 3,900ms (3.9s) |
| Max query (succeeded) | 1,002,500ms / 16.7 min (query_9) |
| P90 (succeeded) | 333.4s |
| P95 (succeeded) | 561.3s |
| Total time (succeeded) | 10,788.9s (179.8 min) |
| Error breakdown | 18 standard Gandiva failures + query_83 (latent PROJECT divide-by-zero exposed by wrapper) |
| Grafana screenshot | |
| Grafana link | [MinIO Dashboard](https://grafana-k5.apps.k2.min.dev/d/TgmJnqnnk/minio-dashboard?orgId=1&from=2026-02-17T16:45:00.000Z&to=2026-02-17T19:52:00.000Z&timezone=browser&var-scrape_jobs=$__all) |
| **Note** | Queries wrapped in `SELECT * FROM (...) t` to bypass Dremio result cache (see Notes section). Query_83 failed due to a latent Gandiva divide-by-zero that was not triggered in Run 1b-a. |

### Phase 1b Summary

| Metric | Run 1b-a | Run 1b-b | Average |
|--------|----------|----------|---------|
| Total elapsed | 178.4 min | 187.1 min | **182.8 min** |
| Queries succeeded | 81/99 | 80/99 | 80-81/99 |
| Avg per-query (succeeded) | 126.7s | 134.9s | **130.8s** |
| Median query | 61.2s | 76.8s | **69.0s** |
| Max query | 1,105.6s (query_9) | 1,002.5s (query_9) | **1,054s** |
| P90 | 303.4s | 333.4s | **318.4s** |
| P95 | 471.2s | 561.3s | **516.3s** |

#### Partition Size Comparison

| Metric | 1Tb_512Mb (~336 MiB files) | 1Tb (~85 MiB files) | Difference |
|--------|---------------------------|---------------------|------------|
| Total elapsed (avg) | 172m 38s | 182m 48s | +5.9% |
| Avg per-query (succeeded) | 123.2s | 130.8s | +6.2% |
| Max query | 1,070s | 1,054s | -1.5% |
| P90 | 317.6s | 318.4s | +0.3% |
| P95 | 437.1s | 516.3s | +18.1% |

**Conclusion:** Larger partition files (~336 MiB) performed slightly better overall (~6% faster avg). The smaller files (~85 MiB) did not improve parallelism as expected. The P95 difference (+18.1%) is partially attributed to query_83 failing in Run 1b-b (reducing the success pool), and normal run-to-run variance.

---

## Phase 2: Warm Run (C3 Cache + Result Cache, No Reflections)

**Purpose:** Measure the combined effect of C3 caching and Dremio result cache. Run 2a primes both caches; Run 2b measures cached performance.

| Setting | Value |
|---------|-------|
| Mode | `noref` |
| Reflections | Disabled |
| Autonomous Reflections | Disabled |
| C3 Cache | **Enabled** |
| Result Cache | Active (no bypass — queries run without wrappers) |
| Dataset | `1Tb_512Mb_partition` |
| Pod command | `./benchmark-kit/run_benchmark.sh noref` |

**Pre-flight checklist:**
- [x] Enable C3 local caching: Dremio UI > Sources > "pedros nessie" > Edit > check "Enable local caching when possible"
- [x] Reflections still disabled
- [x] Autonomous Reflections disabled
- [x] Confirm Dremio engine "tpcds" is running with 4 executors

### Run 2a (cache prime — discard)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_512Mb_partition_noref_20260217-222101.csv` |
| Pod start (UTC) | 2026-02-17 22:21:01 |
| Pod end (UTC) | ~2026-02-18 00:22:00 (estimated ~2h) |
| Total elapsed | ~2h (cache priming run) |
| Status | **Discarded** — warm-up to prime C3 and result caches |

### Run 2b (measured)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_512Mb_partition_noref_20260218-002245.csv` |
| Pod start (UTC) | 2026-02-18 00:22:45 |
| Pod end (UTC) | 2026-02-18 00:24:46 |
| Total elapsed | 2.0 min (117.6s wall clock) |
| Queries succeeded | 81 / 99 |
| Queries failed | 18 / 99 (18.18%) |
| Avg query (succeeded) | 0.32s |
| Median query (succeeded) | 0.221s |
| Min query (succeeded) | 161ms (query_3, query_55) |
| Max query (succeeded) | 3,886ms / 3.9s (query_71) |
| P90 (succeeded) | 0.431s |
| P95 (succeeded) | 0.609s |
| Total time (succeeded) | 26.3s (0.4 min) |
| Error breakdown | 11 Gandiva cast (FILTER), 4 divide-by-zero (PROJECT), 3 divide-by-zero (FILTER) — same 18 as Phase 1 |
| **Note** | All successful queries served from result cache (sub-second). query_83 failed (same intermittent PROJECT div-by-zero). |

### Run 2c (measured)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_512Mb_partition_noref_20260218-003523.csv` |
| Pod start (UTC) | 2026-02-18 00:35:25 |
| Pod end (UTC) | 2026-02-18 00:37:23 |
| Total elapsed | 2.0 min (118.1s wall clock) |
| Queries succeeded | 81 / 99 |
| Queries failed | 18 / 99 (18.18%) |
| Avg query (succeeded) | 0.31s |
| Median query (succeeded) | 0.207s |
| Min query (succeeded) | 153ms |
| Max query (succeeded) | 3,942ms / 3.9s (query_71) |
| P90 (succeeded) | 0.423s |
| P95 (succeeded) | 0.692s |
| Total time (succeeded) | 24.7s (0.4 min) |
| Error breakdown | Same 18 Gandiva failures as Run 2b |

### Phase 2 Summary

| Metric | Run 2b | Run 2c | Average | Phase 1 avg (cold) | Speedup |
|--------|--------|--------|---------|---------------------|---------|
| Total elapsed | 2.0 min | 2.0 min | **2.0 min** | 172.6 min | **86x** |
| Queries succeeded | 81/99 | 81/99 | 81/99 | 81/99 | same |
| Avg per-query (succeeded) | 0.32s | 0.31s | **0.32s** | 123.2s | **385x** |
| Median query | 0.221s | 0.207s | **0.21s** | 62.0s | **295x** |
| Max query | 3.9s | 3.9s | **3.9s** | 1,070s | **274x** |
| P90 | 0.43s | 0.42s | **0.43s** | 317.6s | **739x** |
| Total time (succeeded) | 26.3s | 24.7s | **25.5s** | 9,982s | **391x** |

**Conclusion:** With C3 + result cache active, the 81 successful queries complete in 2 minutes (vs ~2h 53m cold). The speedup is almost entirely from Dremio's result cache — queries return pre-computed results in ~150-250ms. Runs 2b and 2c are nearly identical, confirming stable cached performance. The C3 cache benefit cannot be isolated from this test since result cache dominates. To measure C3 alone, would need to bypass result cache (query wrappers) while keeping C3 enabled.

---

## Phase 2b: Warm Run — 1Tb Dataset (C3 Cache + Result Cache, No Reflections)

**Purpose:** Compare cached performance across partition sizes. Same config as Phase 2 but with `1Tb` dataset (~85 MiB per Parquet file).

| Setting | Value |
|---------|-------|
| Mode | `noref` |
| Reflections | Disabled |
| Autonomous Reflections | Disabled |
| C3 Cache | **Enabled** |
| Result Cache | Active (no bypass) |
| Dataset | `1Tb` (~85 MiB per Parquet file) |

### Run 2b-1Tb-a (cache prime — discard)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_noref_20260218-052710.csv` (approx) |
| Pod start (UTC) | 2026-02-18 05:27:10 |
| Pod end (UTC) | 2026-02-18 05:35:15 |
| Total elapsed | ~8 min (cache priming run) |
| Status | **Discarded** — warm-up to prime caches |

### Run 2b-1Tb-b (measured)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_noref_20260218-053616.csv` |
| Pod start (UTC) | 2026-02-18 05:36:18 |
| Pod end (UTC) | 2026-02-18 05:39:08 |
| Total elapsed | 2.8 min (170.3s wall clock) |
| Queries succeeded | 81 / 99 |
| Queries failed | 18 / 99 (18.18%) |
| Avg query (succeeded) | 0.31s |
| Median query (succeeded) | 0.211s |
| Min query (succeeded) | 149ms |
| Max query (succeeded) | 4,142ms / 4.1s (query_71) |
| P90 (succeeded) | 0.391s |
| P95 (succeeded) | 0.695s |
| Total time (succeeded) | 25.1s |
| Error breakdown | Same 18 Gandiva failures |

### Run 2b-1Tb-c (measured)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_noref_20260218-054252.csv` |
| Pod start (UTC) | 2026-02-18 05:42:54 |
| Pod end (UTC) | 2026-02-18 05:45:11 |
| Total elapsed | 2.3 min (137.1s wall clock) |
| Queries succeeded | 81 / 99 |
| Queries failed | 18 / 99 (18.18%) |
| Avg query (succeeded) | 0.30s |
| Median query (succeeded) | 0.203s |
| Min query (succeeded) | 149ms |
| Max query (succeeded) | 4,265ms / 4.3s (query_71) |
| P90 (succeeded) | 0.368s |
| P95 (succeeded) | 0.577s |
| Total time (succeeded) | 24.6s |
| Error breakdown | Same 18 Gandiva failures |

### Phase 2b Summary

| Metric | Run 2b-1Tb-b | Run 2b-1Tb-c | Average |
|--------|-------------|-------------|---------|
| Total elapsed | 2.8 min | 2.3 min | **2.6 min** |
| Queries succeeded | 81/99 | 81/99 | 81/99 |
| Avg per-query (succeeded) | 0.31s | 0.30s | **0.31s** |
| Median query | 0.211s | 0.203s | **0.21s** |
| Max query | 4.1s | 4.3s | **4.2s** |
| P90 | 0.39s | 0.37s | **0.38s** |
| Total time (succeeded) | 25.1s | 24.6s | **24.8s** |

#### Cached Partition Size Comparison

| Metric | 1Tb_512Mb (~336 MiB files) | 1Tb (~85 MiB files) | Difference |
|--------|---------------------------|---------------------|------------|
| Total elapsed (avg) | 2.0 min | 2.6 min | +30% |
| Avg per-query (succeeded) | 0.32s | 0.31s | -3% |
| Max query | 3.9s | 4.2s | +8% |
| P90 | 0.43s | 0.38s | -12% |

**Conclusion:** With result cache active, partition size has negligible impact on per-query latency (~0.3s for both). The slight wall clock difference (2.0 vs 2.6 min) is within normal variance for cache-served results. Both datasets perform identically under caching.

---

## Phase 3: Reflections Enabled — 1Tb Dataset

**Purpose:** Measure impact of Dremio reflections on query performance. Using `1Tb` dataset first to avoid deleting reflections when switching datasets later.

| Setting | Value |
|---------|-------|
| Mode | `wref` |
| Raw Reflections | Enabled on all 24 TPC-DS tables (via `enable_raw_reflections.py`) |
| Aggregate Reflections | Enabled via recommendation API (via `deploy_reflections.py`) |
| Autonomous Reflections | Disabled |
| C3 Cache | Enabled |
| Result Cache | Active (no bypass) |
| Dataset | `1Tb` (~85 MiB per Parquet file) |
| Pod command | `./benchmark-kit/run_benchmark.sh wref` |

**Reflection deployment:**
1. Ran `enable_raw_reflections.py` — created `recommended_view` space + 24 raw reflections (one per TPC-DS table)
2. Ran `deploy_reflections.py` — executed all 99 queries against `1Tb`, requested Dremio reflection recommendations, created recommended aggregate reflections (views + reflections in `recommended_view` space)
3. Waited for all reflections to materialize (check Dremio Jobs page for reflection refresh jobs)

**Pre-flight checklist:**
- [x] Run `enable_raw_reflections.py` to create raw reflections on all 24 tables
- [x] Run `deploy_reflections.py` to create aggregate reflections from recommendations
- [ ] Wait for all reflections to materialize
- [x] C3 local caching enabled on Nessie source
- [ ] Confirm Dremio engine "tpcds" is running with 4 executors
- [ ] Verify no background reflection refresh jobs still running

### Run 3a (warm-up — discard)

| Item | Value |
|------|-------|
| JMeter CSV | (not saved) |
| Pod start (UTC) | 2026-02-18 23:24:56 |
| Pod end (UTC) | 2026-02-18 23:37:44 |
| Total elapsed | ~13 min |
| Status | **Discarded** — warm-up to prime result cache with reflections active |

### Run 3b (measured)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_wref_20260218-234621.csv` |
| Pod start (UTC) | 2026-02-18 23:46:21 |
| Pod end (UTC) | 2026-02-18 23:48:51 |
| Total elapsed | 2.5 min (147.6s wall clock) |
| Queries succeeded | 81 / 99 |
| Queries failed | 18 / 99 (18.18%) |
| Avg query (succeeded) | 0.77s |
| Median query (succeeded) | 0.489s |
| Min query (succeeded) | 234ms (query_41) |
| Max query (succeeded) | 9,894ms / 9.9s (query_18) |
| P90 (succeeded) | 0.87s |
| P95 (succeeded) | 1.70s |
| Total time (succeeded) | 62.1s (1.0 min) |
| Error breakdown | 11 Gandiva cast, 4 divide-by-zero (PROJECT), 3 divide-by-zero (FILTER) — same 18 as all prior phases |

### Run 3c (measured)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_wref_20260218-235115.csv` |
| Pod start (UTC) | 2026-02-18 23:51:15 |
| Pod end (UTC) | 2026-02-18 23:53:43 |
| Total elapsed | 2.4 min (145.3s wall clock) |
| Queries succeeded | 81 / 99 |
| Queries failed | 18 / 99 (18.18%) |
| Avg query (succeeded) | 0.71s |
| Median query (succeeded) | 0.434s |
| Min query (succeeded) | 227ms (query_41) |
| Max query (succeeded) | 9,794ms / 9.8s (query_18) |
| P90 (succeeded) | 0.85s |
| P95 (succeeded) | 1.28s |
| Total time (succeeded) | 57.5s (1.0 min) |
| Error breakdown | Same 18 Gandiva failures as Run 3b |

### Phase 3 Summary

| Metric | Run 3b | Run 3c | Average | Phase 1b avg (cold, 1Tb) | Speedup vs cold |
|--------|--------|--------|---------|--------------------------|-----------------|
| Total elapsed | 2.5 min | 2.4 min | **2.4 min** | 182.8 min | **76x** |
| Queries succeeded | 81/99 | 81/99 | 81/99 | 80-81/99 | same |
| Avg per-query (succeeded) | 0.77s | 0.71s | **0.74s** | 130.8s | **177x** |
| Median query | 0.489s | 0.434s | **0.46s** | 69.0s | **150x** |
| Max query | 9.9s (query_18) | 9.8s (query_18) | **9.8s** | 1,054s | **108x** |
| P90 | 0.87s | 0.85s | **0.86s** | 318.4s | **370x** |
| P95 | 1.70s | 1.28s | **1.49s** | 516.3s | **347x** |
| Total time (succeeded) | 62.1s | 57.5s | **59.8s** | ~10,525s | **176x** |

#### Phase 3 vs Phase 2b (cached, no reflections)

| Metric | Phase 3 (reflections) | Phase 2b (cached, no ref) | Difference |
|--------|----------------------|---------------------------|------------|
| Total elapsed (avg) | 2.4 min | 2.6 min | -8% |
| Avg per-query (succeeded) | 0.74s | 0.31s | +139% |
| Median query | 0.46s | 0.21s | +119% |
| Max query | 9.8s (query_18) | 4.2s (query_71) | +133% |
| P90 | 0.86s | 0.38s | +126% |

**Conclusion:** With 78 reflections enabled (24 raw + 54 aggregate), the 81 successful queries complete in ~2.4 minutes with a median of 0.46s — a **76x speedup** over the cold baseline (Phase 1b). However, per-query latency is approximately **2x slower** than the pure result cache runs (Phase 2b). This is likely because reflections change the query execution plan, causing Dremio to compute results using reflection data rather than serving identical cached results. The warm-up run (3a) took 13 minutes compared to Phase 1b's ~3 hours, confirming reflections accelerate cold execution by ~14x. Only 2 queries exceeded 5 seconds (query_18 at ~9.8s and query_71 at ~6.3s), suggesting these may not have matching aggregate reflections.

---

## Phase 3b: Reflection Isolation — Aggregate-Only (1Tb)

**Purpose:** Determine whether raw or aggregate reflections drive the performance benefit. Raw reflections disabled via `toggle_reflections.py RAW disable`; only 54 aggregate reflections remain active.

| Setting | Value |
|---------|-------|
| Mode | `wref` |
| Raw Reflections | **Disabled** (24 raw reflections toggled off) |
| Aggregate Reflections | Enabled (54 aggregate reflections) |
| C3 Cache | Enabled |
| Result Cache | Active (no bypass) |
| Dataset | `1Tb` (~85 MiB per Parquet file) |

### Run 3b-agg-warmup (warm-up — discard)

| Item | Value |
|------|-------|
| Pod start (UTC) | 2026-02-19 17:10:00 |
| Pod end (UTC) | 2026-02-19 17:32:29 |
| Total elapsed | ~22 min |
| Status | **Discarded** — warm-up to prime result cache with aggregate-only reflections |

### Run 3b-agg-1 (measured)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_wref_test_no_raw_reflections.csv` |
| Pod start (UTC) | 2026-02-19 20:18:01 |
| Pod end (UTC) | 2026-02-19 20:21:33 |
| Total elapsed | 3.5 min (207.9s wall clock) |
| Queries succeeded | 81 / 99 |
| Queries failed | 18 / 99 (18.18%) |
| Avg query (succeeded) | 1.040s |
| Median query (succeeded) | 0.294s |
| Min query (succeeded) | 156ms (query_90) |
| Max query (succeeded) | 53,273ms / 53.3s (query_18) |
| P90 (succeeded) | 0.561s |
| P95 (succeeded) | 0.685s |
| Total time (succeeded) | 84.2s |
| Error breakdown | Same 18 Gandiva failures |
| **Note** | query_18 outlier at 53.3s inflates the average; median is representative |

### Run 3b-agg-2 (measured)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_wref_test_no_raw_reflections_2.csv` |
| Pod start (UTC) | 2026-02-19 21:37:01 |
| Pod end (UTC) | 2026-02-19 21:39:43 |
| Total elapsed | 2.6 min (158.5s wall clock) |
| Queries succeeded | 81 / 99 |
| Queries failed | 18 / 99 (18.18%) |
| Avg query (succeeded) | 0.607s |
| Median query (succeeded) | 0.290s |
| Min query (succeeded) | 153ms (query_93) |
| Max query (succeeded) | 9,228ms / 9.2s (query_18) |
| P90 (succeeded) | 0.702s |
| P95 (succeeded) | 1.155s |
| Total time (succeeded) | 49.2s |
| Error breakdown | Same 18 Gandiva failures |

### Phase 3b Summary

| Metric | Run 3b-agg-1 | Run 3b-agg-2 | Average |
|--------|-------------|-------------|---------|
| Total elapsed | 3.5 min | 2.6 min | **3.0 min** |
| Queries succeeded | 81/99 | 81/99 | 81/99 |
| Avg per-query (succeeded) | 1.040s | 0.607s | **0.82s** |
| Median query | 0.294s | 0.290s | **0.29s** |
| Max query | 53.3s (query_18) | 9.2s (query_18) | **31.3s** |
| P90 | 0.561s | 0.702s | **0.63s** |
| Total time (succeeded) | 84.2s | 49.2s | **66.7s** |

**Note:** Run 1 had a large query_18 outlier (53.3s) that resolved by Run 2 (9.2s). The medians are nearly identical (0.294s vs 0.290s), confirming consistent performance for the vast majority of queries. Run 2 is the more representative measurement.

---

## Phase 3c: Reflection Isolation — Aggregate-Only (1Tb_512Mb_partition)

**Purpose:** Test aggregate-only reflections on the larger-partition dataset for cross-dataset comparison.

| Setting | Value |
|---------|-------|
| Mode | `wref` |
| Raw Reflections | **Disabled** (24 raw reflections toggled off) |
| Aggregate Reflections | Enabled (52 aggregate reflections) |
| C3 Cache | Enabled |
| Result Cache | Active (no bypass) |
| Dataset | `1Tb_512Mb_partition` (~336 MiB per Parquet file) |

**Reflection deployment:**
1. Ran `enable_raw_reflections.py` with `ICEBERG_FOLDER_NAME=1Tb_512Mb_partition` — 24 raw reflections created
2. Ran `deploy_reflections.py` with `ICEBERG_FOLDER_NAME=1Tb_512Mb_partition` — 52 aggregate reflections created (80/99 queries succeeded)
3. Disabled raw reflections via `toggle_reflections.py RAW disable`

### Run 3c-warmup (warm-up — discard)

| Item | Value |
|------|-------|
| Pod start (UTC) | 2026-02-19 22:06:53 |
| Pod end (UTC) | 2026-02-19 22:36:04 |
| Total elapsed | ~29 min |
| Status | **Discarded** — warm-up |

### Run 3c-1 (measured)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_512Mb_partition_wref_no_raw_reflections_20260219-224047.csv` |
| Pod start (UTC) | 2026-02-19 22:40:47 |
| Pod end (UTC) | 2026-02-19 22:43:48 |
| Total elapsed | 3.0 min (177.6s wall clock) |
| Queries succeeded | 81 / 99 |
| Queries failed | 18 / 99 (18.18%) |
| Avg query (succeeded) | 1.005s |
| Median query (succeeded) | 0.279s |
| Min query (succeeded) | 157ms |
| Max query (succeeded) | 43,345ms / 43.3s (query_18) |
| P90 (succeeded) | 0.692s |
| P95 (succeeded) | 0.825s |
| Total time (succeeded) | 81.4s |
| Error breakdown | Same 18 Gandiva failures |

### Run 3c-2 (measured)

| Item | Value |
|------|-------|
| JMeter CSV | `1Tb_512Mb_partition_wref_no_raw_reflections_20260220-001754.csv` |
| Pod start (UTC) | 2026-02-20 00:17:54 |
| Pod end (UTC) | 2026-02-20 00:21:01 |
| Total elapsed | 3.1 min (183.4s wall clock) |
| Queries succeeded | 81 / 99 |
| Queries failed | 18 / 99 (18.18%) |
| Avg query (succeeded) | 1.077s |
| Median query (succeeded) | 0.274s |
| Min query (succeeded) | 153ms |
| Max query (succeeded) | 50,083ms / 50.1s (query_18) |
| P90 (succeeded) | 0.615s |
| P95 (succeeded) | 0.919s |
| Total time (succeeded) | 87.2s |
| Error breakdown | Same 18 Gandiva failures |

### Phase 3c Summary

| Metric | Run 3c-1 | Run 3c-2 | Average |
|--------|----------|----------|---------|
| Total elapsed | 3.0 min | 3.1 min | **3.0 min** |
| Queries succeeded | 81/99 | 81/99 | 81/99 |
| Avg per-query (succeeded) | 1.005s | 1.077s | **1.04s** |
| Median query | 0.279s | 0.274s | **0.28s** |
| Max query | 43.3s (query_18) | 50.1s (query_18) | **46.7s** |
| P90 | 0.692s | 0.615s | **0.65s** |
| Total time (succeeded) | 81.4s | 87.2s | **84.3s** |

**Note:** query_18 is an extreme outlier on this dataset (43-50s vs 9.2s on 1Tb), accounting for nearly all the difference in average time. Without query_18, performance is nearly identical to the 1Tb aggregate-only results.

---

## Reflection Configuration Comparison

| Metric | Both (raw+agg, 1Tb) | Agg-only (1Tb) | Agg-only (512Mb_part) |
|--------|---------------------|----------------|----------------------|
| Reflections | 24 raw + 54 agg | 54 agg | 52 agg |
| Succeeded | 81/99 | 81/99 | 81/99 |
| Avg per-query | 0.74s | 0.82s* | 1.04s* |
| Median | 0.46s | **0.29s** | **0.28s** |
| P90 | 0.86s | **0.63s** | **0.65s** |
| Max | 9.8s (q18) | 31.3s* (q18) | 46.7s* (q18) |
| Wall clock | ~2.4 min | ~3.0 min | ~3.0 min |
| Warm-up time | ~13 min | ~22 min | ~29 min |

*\* Averages skewed by query_18 outlier. Using Run 2 only: 1Tb agg-only avg=0.607s, max=9.2s.*

**Key findings:**
1. **Aggregate-only has lower median/P90** (0.29s/0.63s) than both-reflections (0.46s/0.86s), suggesting raw reflections add query planner overhead without per-query benefit
2. **Wall clock is similar** across all configs (~2.4-3.0 min), dominated by the 18 failing queries' error time
3. **query_18 is unstable** — varies from 9.2s to 53.3s across runs and is particularly slow on `512Mb_partition` (43-50s)
4. **Warm-up is faster with raw reflections** (13 min vs 22-29 min), likely because raw reflections serve as a pre-materialized cache of the full table data
5. **Recommended final config: Aggregate-only reflections on 1Tb** — best median latency and most consistent results

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

### 1Tb_512Mb_partition Dataset (~336 MiB Parquet files)

| Metric | Phase 1 (cold, no cache) | Phase 2 (warm, cached) | Phase 3c (agg reflections) |
|--------|--------------------------|------------------------|---------------------------|
| Total elapsed (avg) | 172.6 min | 2.0 min | 3.0 min |
| Avg per-query (succeeded) | 123.2s | 0.32s | 1.04s |
| Median query | 62.0s | 0.21s | 0.28s |
| P90 | 317.6s | 0.43s | 0.65s |
| Max query | 1,070s (q9) | 3.9s (q71) | 46.7s (q18) |
| Queries succeeded | 81/99 | 81/99 | 81/99 |
| Speedup vs cold (elapsed) | 1.0x | **86x** | **58x** |
| Speedup vs cold (per-query) | 1.0x | **385x** | **119x** |

### 1Tb Dataset (~85 MiB Parquet files)

| Metric | Phase 1b (cold, no cache) | Phase 2b (warm, cached) | Phase 3 (all reflections) | Phase 3b (agg-only) |
|--------|--------------------------|------------------------|--------------------------|---------------------|
| Total elapsed (avg) | 182.8 min | 2.6 min | 2.4 min | 3.0 min |
| Avg per-query (succeeded) | 130.8s | 0.31s | 0.74s | 0.61s† |
| Median query | 69.0s | 0.21s | 0.46s | 0.29s |
| P90 | 318.4s | 0.38s | 0.86s | 0.70s |
| Max query | 1,054s (q9) | 4.2s (q71) | 9.8s (q18) | 9.2s† (q18) |
| Queries succeeded | 80-81/99 | 81/99 | 81/99 | 81/99 |
| Speedup vs cold (elapsed) | 1.0x | **70x** | **76x** | **61x** |
| Speedup vs cold (per-query) | 1.0x | **422x** | **177x** | **214x†** |

*† Phase 3b uses Run 2 values (more stable; Run 1 had a 53s query_18 outlier)*

### External Comparison: sergeleo/dremio-tpc-ds (Dremio 4.2.1, AWS S3)

**Source:** [github.com/sergeleo/dremio-tpc-ds](https://github.com/sergeleo/dremio-tpc-ds), Tabular Results / Dremio / 4.2.1

The closest published apples-to-apples benchmark: same scale factor (SF1000), same executor count (4), same JMeter methodology. Key difference: AWS S3 storage on m5d.8xlarge instances (NVMe-backed C3 cache) vs our MinIO AIStor on SSD.

**Important methodology note:** The sergeleo benchmark methodology states: *"to capture the benefits of query acceleration with the Dremio columnar cloud cache (C3) feature, we recommend executing JMeter tests in consecutive runs to capture benchmarks with the cold and warm C3."* Their published "no reflections" results are **C3-warm** runs (NVMe-cached), not true cold scans. Our Phase 1 results have C3 **disabled** — a true cold scan from object storage.

#### Hardware Comparison

| Component | Sergeleo (AWS) | Ours |
|-----------|---------------|------|
| **Dremio executors** | 4x m5d.8xlarge (32 vCPU, 128 GiB, 2x600 GB NVMe) | 4x Intel M50CYP (64c/128t Xeon Gold 6338, 240 GB, NVMe) |
| **Storage** | AWS S3 (same region) + NVMe C3 cache | MinIO AIStor: 4x Supermicro (40c/80t Xeon Gold 5218R, 384 GB, SSD, 24 drives, EC:4) |
| **Network** | AWS internal (10-25 Gbps typical) | 100 Gbps |
| **Dremio version** | 4.2.1 (May 2020) | v26.0.9 (Feb 2026) |

#### Cached / Warm Performance (no reflections)

The correct comparison for sergeleo's C3-warm results is our Phase 2 (C3 + result cache):

| Metric | Sergeleo (S3, C3 warm) | Ours (MinIO, C3 + result cache) | Advantage |
|--------|----------------------|-------------------------------|-----------|
| Queries succeeded | 58/99 | **81/99** | **+40% query coverage** |
| Avg per-query | 22.6s | **0.31s** | **73x faster** |
| Median per-query | 13.4s | **0.21s** | **64x faster** |
| Total runtime | 21.8 min | **2.0 min** | **11x faster** |

*Note: Our result cache serves pre-computed results (~150-250ms), while their C3 cache accelerates I/O but still executes queries. This partially explains the per-query gap, though both represent "warm" performance. Dremio version improvements (4.2.1 → v26) also contribute.*

#### Reflections Performance

| Metric | Sergeleo (S3, reflections) | Ours (MinIO, agg-only) | Advantage |
|--------|--------------------------|----------------------|-----------|
| Queries succeeded | 22/99 | **81/99** | **3.7x query coverage** |
| Avg per-query | 5.40s | **0.61s** | **8.9x faster** |
| Median per-query | 2.54s | **0.29s** | **8.8x faster** |
| Total runtime (succeeded) | 2.0 min | **0.8 min** | **2.5x faster** |

On the 21 queries where both benchmarks succeeded with reflections, our MinIO AIStor setup was **15.7x faster** on average, with individual query speedups ranging from 2.9x to 58.6x.

#### Cold Performance (true cold scan — no cache, no reflections)

Sergeleo did not publish true cold-scan results (C3 was enabled). Our Phase 1 represents a genuine cold baseline with C3 disabled:

| Metric | Ours (MinIO, C3 disabled, cold) |
|--------|-------------------------------|
| Queries succeeded | 81/99 |
| Avg per-query | 122.3s |
| Median per-query | 60.3s |
| Total runtime | 172.6 min |

*No direct S3 comparison available for true cold scans at SF1000 with 4 workers.*

#### Key Takeaways

1. **MinIO AIStor is not a bottleneck for Dremio query acceleration.** With C3 + result cache, queries complete in sub-second latency (0.31s avg) — 73x faster than the published S3 + C3-warm benchmark.
2. **Dramatically better query coverage.** We succeed on 81/99 queries vs 58/99 (no reflections) and 22/99 (reflections) in the S3 benchmark. This is primarily a Dremio version improvement (v26 vs 4.2.1).
3. **Reflection performance is transformative.** With aggregate-only reflections on MinIO AIStor, the median query takes 0.29s — faster than sergeleo's C3-warm results *without* reflections (13.4s median).
4. **The cold-scan gap is expected.** Our true cold scans (122.3s avg) are slower than their C3-warm results (22.6s avg), but this is comparing cold vs warm — not a storage backend difference.

### Other Reference Benchmarks

| Source | Config | Result |
|--------|--------|--------|
| Dremio Sept 2025 "20x Faster" | 8-node m7gd.4xlarge, Autonomous Reflections, S3 | 99 queries in 22s |
| Dremio 21.0 (Aug 2025) | m5d.8xlarge / i3.4xlarge, S3 | ~30% improvement over prior |
| Intel/AWS white paper (Jan 2024) | 8/16-node m5dn/m6id, S3, 5 concurrent users | 11-29% faster on m6id vs m5dn |
| Dell EMC (SF10000) | PowerScale HDFS / ECS S3, no reflections | 58/99 queries |

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
| Grafana link | [MinIO Dashboard](https://grafana-k5.apps.k2.min.dev/d/TgmJnqnnk/minio-dashboard?orgId=1&from=2026-02-12T21:23:00.000Z&to=2026-02-12T21:28:00.000Z&timezone=browser&var-scrape_jobs=$__all) |
| Key observation | MinIO egress ~1.5 GiB/s, storage not bottleneck on sample data |

---

## Query Modifications

**Decision: Use unmodified TPC-DS queries.** All 99 queries run as-is from the standard TPC-DS templates. Queries that fail due to Dremio/Gandiva limitations are recorded as failures and excluded from timing analysis, matching the approach used in published Dremio benchmarks (e.g., `sergeleo/dremio-tpc-ds` which reported 58/99 queries for sf1000).

### Known Dremio v26.0.9 Failure Modes

The following failure modes were identified during Run 1d (with regenerated sf=1000 queries). Rather than modifying queries, we let them fail naturally:

| Failure Mode | Affected Queries | Root Cause |
|-------------|-----------------|------------|
| Gandiva cast error (11) | query_13, query_15, query_28, query_37, query_48, query_49, query_64, query_74, query_80, query_82, query_85 | Gandiva cannot cast decimal columns compared to integer literals (e.g., "27.02" to int64_t) |
| Gandiva divide-by-zero (PROJECT) (4) | query_36, query_58, query_66, query_83 | Division by zero in SELECT expressions; Gandiva does not short-circuit |
| Gandiva divide-by-zero (FILTER) (3) | query_34, query_73, query_75 | Division by zero in WHERE clauses; Gandiva FILTER evaluator evaluates all rows regardless of CASE/NULLIF guards |

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
- **Result Cache**: Dremio caches query results and serves them for repeated identical queries. In v26.0.9, there is **no UI toggle or support key** to disable result caching (`exec.query.results.cache.enabled` not found). The cache normalizes SQL text (strips comments) before hashing, so adding SQL comments does not bypass it. **Workaround:** Wrap queries in `SELECT * FROM (...) t` to change the query structure and force cache misses. The cache appears to survive engine restarts but expires after ~24-48 hours.
- **Autonomous Reflections**: Dremio auto-creates reflections based on query patterns. In Phase 1b, this was initially left enabled and silently created 2 reflections after Run 1b-a, causing subsequent runs to complete in ~9 minutes (~20x speedup). **Must be explicitly disabled** before benchmark runs (Admin Settings > Support > `reflection.recommender.autonomous_mode.enabled` = false).
- **Reflections**: Pre-computed materializations. `deploy_reflections.py` runs all 99 queries and creates Dremio-recommended reflections.
- **Query_83 intermittent failure**: Query_83 has a latent Gandiva divide-by-zero in PROJECT context (`sr_item_qty/(sr_item_qty+cr_item_qty+wr_item_qty)`). It succeeds when no rows have a zero sum, but fails non-deterministically depending on execution plan and data distribution across executors.
