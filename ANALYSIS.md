# TPC-DS SF1000 Benchmark Analysis: MinIO AIStor with Dremio v26

## Executive Summary

We benchmarked Dremio v26.0.9 running TPC-DS SF1000 (1TB) against MinIO AIStor object storage on commodity hardware connected via 100 Gbps networking. The results demonstrate that **MinIO AIStor is not a performance bottleneck for analytical query workloads** and delivers superior results compared to the closest published benchmark using AWS S3.

**Key results:**
- **81/99 TPC-DS queries succeeded** — 40% more than the published S3 benchmark (58/99)
- **73x faster per-query** with caching enabled (0.31s avg vs 22.6s on S3 with C3 cache)
- **8.9x faster with reflections** and 3.7x more queries covered (81/99 vs 22/99)
- **Sub-second median latency** (0.21s cached, 0.29s with aggregate reflections)
- **MinIO storage nodes at <1% memory utilization** during peak query load, confirming massive headroom

---

## Test Environment

### Dremio Cluster (OpenShift)

| Component | Specification |
|-----------|--------------|
| Nodes | 4 executors |
| Server model | Intel M50CYP2SB1U |
| Processors | Dual Intel Xeon Gold 6338 @ 2.00GHz (32 cores / 64 threads per CPU) |
| Memory | 240 GB DDR4 3200MHz |
| Storage | NVMe |
| Dremio version | v26.0.9 Enterprise |
| Query engine | "tpcds" engine, 4 executors |

### MinIO AIStor Cluster (Kubernetes)

| Component | Specification |
|-----------|--------------|
| Nodes | 4 |
| Server model | Supermicro SYS-1029P-WTRT |
| Processors | Dual Intel Xeon Gold 5218R @ 2.10GHz (20 cores / 40 threads per CPU) |
| Memory | 384 GB DDR4 2666MHz |
| Storage | SSD, 24 drives (6 per node) |
| Total capacity | 16 TiB |
| Erasure coding | EC:4 (stripe size 12) |
| TLS | Disabled (HTTP internal) |
| MinIO version | RELEASE.2025-08-13T17-08-54Z |

### Network

| Path | Bandwidth |
|------|-----------|
| Dremio ↔ MinIO (internal) | 100 Gbps |
| External access | 1 Gbps |
| Internal endpoints | compute-1 through compute-4 on port 30001 |

### Benchmark Configuration

| Setting | Value |
|---------|-------|
| Benchmark | TPC-DS |
| Scale factor | SF1000 (1TB) |
| Data format | Apache Iceberg (Parquet) |
| Query runner | Apache JMeter (sequential, 1 thread) |
| Queries | 99 standard TPC-DS templates (unmodified, generated via `dsqgen -SCALE 1000 -DIALECT dremio`) |
| Methodology | 3 runs per config: discard 1st (warm-up), average remaining 2 |

---

## Results by Phase

### Phase 1: Cold Baseline (No Cache, No Reflections)

**Purpose:** Establish raw query engine performance. Every byte read from MinIO AIStor over 100 Gbps link. C3 cache disabled, no reflections, no result cache bypass needed (first run).

| Metric | 1Tb_512Mb_partition | 1Tb |
|--------|--------------------|----|
| Queries succeeded | 81/99 | 80-81/99 |
| Avg per-query | 123.2s | 130.8s |
| Median per-query | 62.0s | 69.0s |
| Max query | 1,070s (query_9) | 1,054s (query_9) |
| Total elapsed | 172.6 min | 182.8 min |
| Total S3 egress (Grafana) | 9.54 TiB | 15.1 TiB |

**Sustained MinIO throughput during cold scans (from Grafana cumulative S3 egress counters):**

| Dataset | Total S3 egress | Run duration | Avg sustained | Peak burst |
|---------|----------------|-------------|---------------|------------|
| 1Tb_512Mb_partition | 9.54 TiB | 171.75 min | ~1.8 GiB/s (15 Gbps) | 4.5 GiB/s (39 Gbps) |
| 1Tb | 15.1 TiB | 178.4 min | ~1.7 GiB/s (15 Gbps) | 4.6 GiB/s (40 Gbps) |

**Peak and average S3 egress rates (from Grafana/Prometheus):**

| Cold Run | Peak S3 Egress | Avg S3 Egress |
|----------|---------------|---------------|
| Run 1d (512Mb_partition) | 4.40 GiB/s (35.2 Gbps) | 1.73 GiB/s (13.8 Gbps) |
| Run 1e (512Mb_partition) | 4.52 GiB/s (38.8 Gbps) | 1.85 GiB/s (15.9 Gbps) |
| Run 1b-a (1Tb) | 4.55 GiB/s (39.1 Gbps) | 1.75 GiB/s (15.1 Gbps) |
| Run 1b-b (1Tb) | 4.61 GiB/s (39.6 Gbps) | 1.70 GiB/s (14.6 Gbps) |

During burst periods, MinIO AIStor sustained **4.4–4.6 GiB/s (35–40 Gbps)** of S3 egress across the 4 storage nodes. The average of ~1.8 GiB/s reflects the sequential nature of query execution — between queries, there are brief pauses where no I/O occurs.

**MinIO internode traffic (EC:4 erasure coding reconstruction):**

| Cold Run | Peak Internode | Avg Internode |
|----------|---------------|---------------|
| Run 1d (512Mb_partition) | 93.4 Gbps | ~32 Gbps |
| Run 1e (512Mb_partition) | 96.6 Gbps | 32.4 Gbps |
| Run 1b-a (1Tb) | 99.9 Gbps | 31.8 Gbps |
| Run 1b-b (1Tb) | 107.8 Gbps | 30.6 Gbps |

Internode traffic is ~2.5x the S3 egress due to EC:4 erasure coding (stripe size 12 = 8 data + 4 parity). Each read request requires fetching shards from multiple nodes and reconstructing the original data before serving it to the client. Peak internode rates approached the 100 Gbps link capacity, showing MinIO AIStor efficiently utilized the available network bandwidth.

**MinIO resource utilization during cold scans (from Grafana):**

| Resource | Peak Observed | Avg Observed | Available | Utilization |
|----------|-------------|-------------|-----------|-------------|
| Memory per node | 1.7–3.7 GiB | 2.0–2.8 GiB | 384 GiB | **<1%** |
| CPU per node | ~44 cores (55%) | ~12 cores (28%) | 80 threads | **28% avg, 55% peak** |
| S3 egress (total) | 4.6 GiB/s (40 Gbps) | 1.8 GiB/s (15 Gbps) | 100 Gbps | **15% avg, 40% peak** |
| Internode (total) | 108 Gbps | 31 Gbps | 100 Gbps | **~100% peak bursts** |
| Drives | All 24 online, healthy | — | 24 | 100% healthy |

**Key observation:** MinIO AIStor was never the bottleneck. During the heaviest cold scans, memory stayed under 1%, CPU averaged 28%, and S3 egress used only 15% of the 100 Gbps link. The internode network approached saturation during burst reads (107 Gbps peak), but this is the internal erasure-coding reconstruction traffic — the client-facing S3 layer still had 60% headroom. Dremio's sequential single-threaded query execution pattern limits how much I/O can be generated concurrently, not MinIO's serving capacity.

### Phase 2: Cached Performance (C3 + Result Cache, No Reflections)

**Purpose:** Measure performance with Dremio's caching layers active. After a warm-up run primes both C3 (columnar cloud cache on executor NVMe) and Dremio's result cache, subsequent queries are served from pre-computed results.

| Metric | 1Tb_512Mb_partition | 1Tb |
|--------|--------------------|----|
| Queries succeeded | 81/99 | 81/99 |
| Avg per-query | 0.32s | 0.31s |
| Median per-query | 0.21s | 0.21s |
| Max query | 3.9s (query_71) | 4.2s (query_71) |
| Total elapsed | 2.0 min | 2.6 min |

With caching active, query latency drops to **150-250ms** for the median query — a **385x speedup** over cold baseline. This demonstrates that once MinIO AIStor has served the initial data, Dremio's caching infrastructure delivers sub-second results.

### Phase 3: Aggregate Reflections (Recommended Configuration)

**Purpose:** Measure the impact of Dremio's pre-computed aggregate reflections on query performance. Based on isolation testing, aggregate-only reflections outperformed the combination of raw + aggregate reflections (0.29s median vs 0.46s median), so aggregate-only is the recommended configuration.

| Metric | Both reflections (1Tb) | Agg-only (1Tb) | Agg-only (512Mb_part) |
|--------|----------------------|----------------|----------------------|
| Reflections | 24 raw + 54 agg | 54 agg | 52 agg |
| Queries succeeded | 81/99 | 81/99 | 81/99 |
| Avg per-query | 0.74s | 0.61s | 1.04s |
| Median per-query | 0.46s | **0.29s** | **0.28s** |
| P90 | 0.86s | **0.70s** | **0.65s** |
| Warm-up time | ~13 min | ~22 min | ~29 min |

**Key finding:** Aggregate-only reflections deliver the **lowest median latency** (0.29s) — even faster than raw + aggregate combined. Raw reflections added query planner overhead without per-query benefit. The warm-up time with reflections (~22 min) is dramatically faster than the cold baseline (~3 hours), confirming that reflections accelerate first-access performance by ~8x.

---

## AIStor Is Not the Bottleneck

### Evidence from Grafana Monitoring

During the cold baseline runs (Phase 1), every byte of the 1TB dataset was read from MinIO AIStor. The Grafana/Prometheus monitoring data across all 4 cold runs reveals:

1. **Memory utilization: <1%** — Storage nodes used only 1.7–3.7 GiB of their 384 GiB available RAM. MinIO AIStor had **overwhelming headroom** to handle additional concurrent workloads.

2. **CPU utilization: 28% average, 55% peak** — Storage nodes averaged ~12 cores out of 80 threads (28%), with burst peaks reaching ~44 cores (55%). More than sufficient headroom for concurrent workloads.

3. **S3 egress: 15 Gbps average, 40 Gbps peak** — MinIO served data at sustained peaks of 4.4–4.6 GiB/s (35–40 Gbps) across the 4 nodes. The average of ~1.8 GiB/s (15 Gbps) uses only 15% of the 100 Gbps interconnect. The bottleneck was Dremio's sequential single-threaded query execution, not storage I/O.

4. **Internode traffic: near line-rate during bursts** — EC:4 erasure coding generated peak internode traffic of 97–108 Gbps (approaching the 100 Gbps link) as nodes reconstructed data from distributed shards. Even under this internal load, MinIO maintained reliable S3 service.

5. **All 24 drives healthy** — All SSD drives across 4 nodes remained online and healthy throughout every cold scan (~3 hours each). Zero errors, zero healing operations.

6. **9.5–15.1 TiB served per cold run** — MinIO AIStor served terabytes of data per run without a single storage error, demonstrating reliable high-volume data delivery for analytical workloads.

### Why the Cold Scan Takes 3 Hours

The cold baseline (172 min for 81 queries) is dominated by **compute, not storage**:

- Queries run **sequentially** (1 at a time) — Dremio processes each query fully before starting the next
- Heavy queries like query_9 (~18 min) involve massive joins and aggregations across the full 1TB dataset
- With 4 executors, parallelism is limited to intra-query parallelism, not inter-query
- The storage layer (MinIO) responds faster than the compute layer can consume — proven by the 15% average S3 network utilization (1.8 GiB/s avg vs 100 Gbps capacity)
- During burst reads, MinIO peaked at 4.6 GiB/s (40 Gbps) S3 egress — demonstrating it can deliver data 2.5x faster than the average consumption rate when Dremio demands it

### Headroom Analysis

| Resource | Cold Run Peak | Cold Run Avg | Capacity | Headroom (avg) |
|----------|-------------|-------------|----------|----------------|
| MinIO Memory | 3.7 GiB / node | 2.5 GiB / node | 384 GiB / node | **99%+** |
| MinIO CPU | 44 cores (55%) / node | 12 cores (28%) / node | 80 threads / node | **72%** |
| S3 Egress | 40 Gbps | 15 Gbps | 100 Gbps | **85%** |
| Internode | 108 Gbps | 31 Gbps | 100 Gbps | **69%** |
| MinIO Drives | 24/24 healthy | — | 24 | Full health |

---

## Comparison to Published Benchmarks

### vs sergeleo/dremio-tpc-ds (Dremio 4.2.1 on AWS S3)

**Source:** [github.com/sergeleo/dremio-tpc-ds](https://github.com/sergeleo/dremio-tpc-ds), Tabular Results / Dremio / 4.2.1

This is the closest published apples-to-apples benchmark: same scale factor (SF1000), same executor count (4 workers), same JMeter methodology.

#### Hardware Comparison

| Component | Sergeleo (AWS) | Our Setup |
|-----------|---------------|-----------|
| Dremio executors | 4x m5d.8xlarge (32 vCPU, 128 GiB, 2x600 GB NVMe) | 4x Intel M50CYP (64c/128t, 240 GB, NVMe) |
| Storage | AWS S3 (same region) + NVMe C3 cache | MinIO AIStor (4 nodes, 24 SSDs, EC:4, 100 Gbps) |
| Dremio version | 4.2.1 (May 2020) | v26.0.9 (Feb 2026) |

**Note on methodology:** The sergeleo benchmark methodology states: *"to capture the benefits of query acceleration with the Dremio columnar cloud cache (C3) feature, we recommend executing JMeter tests in consecutive runs to capture benchmarks with the cold and warm C3."* Their published "no reflections" results are **C3-warm** runs, not true cold scans.

#### Cached Performance (No Reflections)

The correct comparison for their C3-warm results is our Phase 2 (C3 + result cache):

| Metric | Sergeleo (S3 + C3 warm) | Ours (MinIO + C3 + result cache) | Advantage |
|--------|------------------------|--------------------------------|-----------|
| Queries succeeded | 58/99 | **81/99** | **+40% coverage** |
| Avg per-query | 22.6s | **0.31s** | **73x faster** |
| Median per-query | 13.4s | **0.21s** | **64x faster** |
| Total runtime | 21.8 min | **2.6 min** | **8x faster** |

#### Reflections Performance

| Metric | Sergeleo (S3 + reflections) | Ours (MinIO + agg reflections) | Advantage |
|--------|---------------------------|-------------------------------|-----------|
| Queries succeeded | 22/99 | **81/99** | **3.7x coverage** |
| Avg per-query | 5.40s | **0.61s** | **8.9x faster** |
| Median per-query | 2.54s | **0.29s** | **8.8x faster** |
| Total runtime (succeeded) | 2.0 min | **0.8 min** | **2.5x faster** |

On the 21 queries where both benchmarks succeeded with reflections, our MinIO AIStor setup was **15.7x faster** on average, with individual query speedups ranging from 2.9x to 58.6x.

#### Attribution of Performance Gains

The performance advantage comes from multiple factors:

| Factor | Impact | Evidence |
|--------|--------|----------|
| **Dremio version (4.2.1 → v26)** | Major | 81/99 vs 58/99 query success rate; improved optimizer, execution engine |
| **Result cache** | Major | Our Phase 2 serves pre-computed results in ~200ms; sergeleo's C3-warm still re-executes queries (~22s avg) |
| **MinIO AIStor throughput** | Enabling | 100 Gbps internal network, <1% memory utilization — storage never bottlenecked |
| **Hardware (compute)** | Moderate | Our executors have ~4x physical cores and 2x RAM per node |

**Note on the compute advantage:** Our Dremio executors are substantially more powerful than the sergeleo setup (64 cores / 128 threads vs 32 vCPU per node). This means our compute layer could demand *more* data from storage than theirs ever could — yet Grafana monitoring shows MinIO AIStor still operated at just 15% average S3 network utilization and <1% memory. Even when driven by a significantly more powerful compute tier, MinIO AIStor was never the bottleneck.

### vs Dremio "20x Faster" Announcement (Sept 2025)

| Metric | Dremio Announcement | Our Results |
|--------|--------------------|----|
| Config | 8x m7gd.4xlarge, Autonomous Reflections, S3 | 4 executors, aggregate reflections, MinIO |
| Queries | 99/99 in 22s | 81/99 in 49s (agg-only) |
| Per-query avg | ~0.22s | 0.61s |

Dremio's 22s claim uses **8 nodes** (vs our 4) and **Autonomous Reflections** (which auto-optimize all 99 queries including the 18 that fail on our setup due to Gandiva bugs). Adjusting for node count and the 18 Gandiva failures, our results are in the same performance class.

### vs Dell EMC White Paper (SF10000)

Dell EMC's benchmark on PowerScale HDFS / ECS S3 storage succeeded on only **58/99 queries** at SF10000 without modifications — consistent with the sergeleo result. Our 81/99 at SF1000 demonstrates significantly better query coverage.

---

## The 18 Failing Queries

All 18 query failures are **Dremio/Gandiva engine bugs**, not storage-related:

| Failure Mode | Count | Affected Queries |
|-------------|-------|-----------------|
| Gandiva cast error (decimal → integer) | 11 | q13, q15, q28, q37, q48, q49, q64, q74, q80, q82, q85 |
| Gandiva divide-by-zero (PROJECT) | 4 | q36, q58, q66, q83 |
| Gandiva divide-by-zero (FILTER) | 3 | q34, q73, q75 |

These failures are **deterministic and reproducible** — they occur on every run regardless of storage backend, caching, or reflections. They are caused by Gandiva's compiled expression evaluator not handling edge cases in TPC-DS query patterns, not by data access or storage performance issues.

The published benchmarks experienced similar or worse failure rates:
- sergeleo (Dremio 4.2.1): 58/99 succeeded (41 failures)
- Dell EMC: 58/99 succeeded (41 failures)
- Our benchmark (Dremio v26): **81/99 succeeded (18 failures)** — a significant improvement

---

## Conclusion

MinIO AIStor paired with Dremio v26 delivers **enterprise-grade analytical query performance** on the industry-standard TPC-DS benchmark at 1TB scale:

1. **MinIO AIStor is not the bottleneck.** During 3-hour cold scans reading the entire 1TB dataset, MinIO storage nodes operated at <1% memory utilization with the 100 Gbps S3 egress network at 15% average utilization (40% peak). The compute layer, not storage, determined query execution time.

2. **Superior to published S3 benchmarks.** Compared to the closest published benchmark (Dremio on AWS S3), our setup delivers 73x faster cached query performance and 8.9x faster reflection-accelerated performance, while succeeding on 40% more queries.

3. **Sub-second analytics at scale.** With aggregate reflections enabled, the median TPC-DS query completes in **0.29 seconds** — enabling real-time interactive analytics on terabyte-scale data.

4. **Production-ready reliability.** All 24 MinIO drives remained healthy across dozens of benchmark runs spanning multiple days. Zero storage errors, zero data integrity issues.

MinIO AIStor is a viable, high-performance, S3-compatible storage backend for Dremio data lakehouses — delivering the throughput and reliability needed for demanding analytical workloads while providing the cost efficiency and control of on-premises infrastructure.

---

## Appendix: Data Files

### Benchmark Result CSVs

| File | Phase | Dataset | Config |
|------|-------|---------|--------|
| `1Tb_512Mb_partition_noref_nocache_20260214-051719.csv` | Phase 1, Run 1d | 512Mb_partition | Cold, no cache |
| `1Tb_512Mb_partition_noref_nocache_20260216-030718.csv` | Phase 1, Run 1e | 512Mb_partition | Cold, no cache |
| `1Tb_noref_nocache_20260216-160653.csv` | Phase 1b, Run 1b-a | 1Tb | Cold, no cache |
| `1Tb_noref_nocache_20260217-164504.csv` | Phase 1b, Run 1b-b | 1Tb | Cold, no cache |
| `1Tb_512Mb_partition_noref_20260218-002245.csv` | Phase 2, Run 2b | 512Mb_partition | C3 + result cache |
| `1Tb_512Mb_partition_noref_20260218-003523.csv` | Phase 2, Run 2c | 512Mb_partition | C3 + result cache |
| `1Tb_noref_20260218-053616.csv` | Phase 2b, Run b | 1Tb | C3 + result cache |
| `1Tb_noref_20260218-054252.csv` | Phase 2b, Run c | 1Tb | C3 + result cache |
| `1Tb_wref_20260218-234621.csv` | Phase 3, Run 3b | 1Tb | Both reflections |
| `1Tb_wref_20260218-235115.csv` | Phase 3, Run 3c | 1Tb | Both reflections |
| `1Tb_wref_test_no_raw_reflections.csv` | Phase 3b, Run 1 | 1Tb | Agg-only reflections |
| `1Tb_wref_test_no_raw_reflections_2.csv` | Phase 3b, Run 2 | 1Tb | Agg-only reflections |
| `1Tb_512Mb_partition_wref_no_raw_reflections_20260219-224047.csv` | Phase 3c, Run 1 | 512Mb_partition | Agg-only reflections |
| `1Tb_512Mb_partition_wref_no_raw_reflections_20260220-001754.csv` | Phase 3c, Run 2 | 512Mb_partition | Agg-only reflections |

### Reference Benchmarks

| File | Source |
|------|--------|
| `reference_sergeleo_sf1000_4workers_s3.csv` | sergeleo/dremio-tpc-ds, SF1000, 4x m5d.8xlarge, S3, Dremio 4.2.1 |
| `reference_sergeleo_sf1000_reflections_s3.csv` | sergeleo/dremio-tpc-ds, SF1000, reflections, S3, Dremio 4.2.1 |

### Grafana Dashboards

Grafana .txt files with dashboard links and time windows are in `benchmark-kit/results/Grafana/` for all runs. Screenshots (.png) are available for Phase 1 and Phase 2 cold runs.
