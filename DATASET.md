# TPC-DS Dataset Documentation

## Overview

This repository contains tooling for deploying TPC-DS benchmark data as Apache Iceberg tables in Dremio.

| Property | Value |
|----------|-------|
| Benchmark | TPC-DS |
| Scale Factor | SF1000 (1TB) |
| Total Tables | 25 |
| Total Rows | 6,347,386,006 |

---

## Infrastructure

### OpenShift Cluster (Dremio)

| Component | Specification |
|-----------|---------------|
| Nodes | 4 |
| Server Model | Intel M50CYP2SB1U |
| Processors | Dual Intel Xeon Gold 6338 @ 2.00GHz |
| Cores/Threads | 32 cores / 64 threads per CPU |
| Memory | 240 GB DDR4 3200MHz |
| Storage | NVMe |

### Kubernetes Cluster (MinIO AIStor)

| Component | Specification |
|-----------|---------------|
| Nodes | 4 |
| Server Model | Supermicro SYS-1029P-WTRT |
| Processors | Dual Intel Xeon Gold 5218R @ 2.10GHz |
| Cores/Threads | 20 cores / 40 threads per CPU |
| Memory | 384 GB DDR4 2666MHz |
| Storage | SSD |

### Network

| Connection | Speed |
|------------|-------|
| Dremio ↔ MinIO (internal) | 100 Gbps |
| External access | 1 Gbps |

Internal endpoints (100Gbps):
- `compute-1.min.dc:30001`
- `compute-2.min.dc:30001`
- `compute-3.min.dc:30001`
- `compute-4.min.dc:30001`

---

## Environment

### Storage: MinIO AIStor (S3-Compatible)

| Setting | Value |
|---------|-------|
| Endpoint (internal) | `http://compute-1.min.dc:30001` |
| Endpoint (external) | `https://storage.k5.min.dev` |
| Protocol | S3-compatible API |
| Storage Pools | 4 |
| Drives | 24 (6 per node) |
| Total Capacity | 16 TiB |
| Erasure Coding | EC:4 |
| Erasure Stripe Size | 12 |

### Buckets

| Bucket | Purpose |
|--------|---------|
| `tpcds` | Source Parquet data |
| `iceberg` | Iceberg table storage |

### Dremio

| Setting | Value |
|---------|-------|
| Version | 26.0.9-202512010302320647-6cf75e74 |
| URL | `http://dremio-dremio-v26.apps.k2.min.dc/` |
| Cluster Type | Kubernetes |
| Sources | `tpcds` (S3), `pedros nessie` (Nessie catalog) |

#### Engine Configuration: "tpcds"

| Setting | Value |
|---------|-------|
| Executors | 4 |
| Engine Size | Medium |
| Memory per Executor | 120 GB |
| Cores per Executor | 30 |
| Max Width per Executor | 23 |
| Spill Volume | 500 GB |
| Auto Start | Enabled |
| Auto Stop | Enabled (15 min idle) |

**Executor Nodes:**

| Node | Hostname | CPU | Memory |
|------|----------|-----|--------|
| 0 | dremio-executor-tpcds-000-0 | 6.7% | 11.5% |
| 1 | dremio-executor-tpcds-000-1 | 10% | 11.5% |
| 2 | dremio-executor-tpcds-000-2 | 13.3% | 11.5% |
| 3 | dremio-executor-tpcds-000-3 | 0% | 11.6% |

#### Spill Settings

| Setting | Value |
|---------|-------|
| Spill Limit | 1 GB |
| Join Spill | Enabled |
| Join Spill Partitions | 8 |
| Join Spill Page Size | 256 KB |
| Sort Spill Compression | Enabled |
| Sort Micro Spill | Enabled |

#### Memory Settings

| Setting | Value |
|---------|-------|
| Spillable Operators | Enabled |
| Max Memory Grant | 40 MB |
| Free Memory Watermark | 20% |
| Absolute Free Memory Watermark | 4 GB |
| Heap Monitor Threshold | 85% |
| Low Memory Threshold | 75% |

#### Workload Management Queues

| Queue | CPU Tier | Max Concurrent | Engine |
|-------|----------|----------------|--------|
| High Cost User Queries | MEDIUM | 10 | tpcds |
| Low Cost User Queries | MEDIUM | 100 | tpcds |
| UI Previews | CRITICAL | 100 | tpcds |
| High Cost Reflections | BACKGROUND | 1 | default |
| Low Cost Reflections | BACKGROUND | 10 | default |

### Nessie Catalog

[Nessie](https://projectnessie.org/) is a transactional catalog for data lakes that provides Git-like versioning for Iceberg tables.

| Setting | Value |
|---------|-------|
| Source Name | `pedros nessie` |
| Catalog Type | Nessie |
| Internal Endpoint | `http://nessie.nessie-ns.svc.cluster.local:19120/api/v2` |
| External Endpoint | `https://nessie.apps.k2.min.dev` |
| Storage Location | `s3://iceberg/` (MinIO) |

**Key Features:**
- **Git-like branching**: Create branches to test schema changes or new data without affecting production
- **Time travel**: Query data as it existed at any point in time
- **Atomic commits**: Multi-table transactions with rollback capability
- **Audit history**: Full commit history of all changes to tables

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                        Dremio v26                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐         ┌─────────────────────────┐   │
│  │  tpcds (S3)     │         │  pedros nessie (Nessie) │   │
│  │  Source Parquet │         │  Iceberg Catalog        │   │
│  └────────┬────────┘         └───────────┬─────────────┘   │
└───────────┼──────────────────────────────┼─────────────────┘
            │                              │
            ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     MinIO (S3-Compatible)                   │
├─────────────────────┬───────────────────────────────────────┤
│  tpcds bucket       │  iceberg bucket                       │
│  └── sample_1Tb/    │  └── <nessie metadata & data files>   │
│      └── *.parquet  │                                       │
└─────────────────────┴───────────────────────────────────────┘
```

---

## Data Locations

### Source Parquet Data

The TPC-DS Parquet files are stored in the `tpcds` bucket with three available configurations:

| Folder | Size | Parquet File Size | Description |
|--------|------|-------------------|-------------|
| `sample_1Tb` | ~1 GB | ~59 KB | Small sample for testing |
| `1Tb` | 1 TB | ~85 MiB | Full dataset, standard chunks |
| `1Tb_512Mb_partition` | 1 TB | ~336 MiB | Full dataset, larger chunks (recommended) |

The `1Tb_512Mb_partition` configuration is recommended for query engines as larger file chunks improve performance.

### Iceberg Tables

Iceberg tables are created in the Nessie catalog under:
```
"pedros nessie".<folder_name>.<table_name>
```

---

## Table Inventory

### Row Counts (SF1000)

| Table | Row Count | Type |
|-------|-----------|------|
| store_sales | 2,879,987,999 | Fact (Partitioned) |
| catalog_sales | 1,439,980,416 | Fact (Partitioned) |
| web_sales | 720,000,376 | Fact (Partitioned) |
| inventory | 783,000,000 | Fact (Partitioned) |
| store_returns | 287,999,764 | Fact (Partitioned) |
| catalog_returns | 143,996,756 | Fact (Partitioned) |
| web_returns | 71,997,522 | Fact (Partitioned) |
| customer | 12,000,000 | Dimension |
| customer_address | 6,000,000 | Dimension |
| customer_demographics | 1,920,800 | Dimension |
| date_dim | 73,049 | Dimension |
| time_dim | 86,400 | Dimension |
| item | 300,000 | Dimension |
| warehouse | 20 | Dimension |
| store | 1,002 | Dimension |
| web_site | 54 | Dimension |
| web_page | 3,000 | Dimension |
| catalog_page | 30,000 | Dimension |
| call_center | 42 | Dimension |
| promotion | 1,500 | Dimension |
| household_demographics | 7,200 | Dimension |
| income_band | 20 | Dimension |
| ship_mode | 20 | Dimension |
| reason | 65 | Dimension |
| dbgen_version | 1 | Metadata |
| **TOTAL** | **6,347,386,006** | |

---

## Partitioning Strategy

### Source Parquet Data

The source Parquet data uses **Hive-style partitioning** for fact tables. Partition directories are named using the pattern:
```
<partition_column>=<value>/
```

Example for `store_sales`:
```
tpcds/sample_1Tb/store_sales/ss_sold_date_sk=2450816/
tpcds/sample_1Tb/store_sales/ss_sold_date_sk=2450817/
...
```

The partition column value is extracted from the directory name during Iceberg table creation.

### Iceberg Tables

#### Partitioned Tables (7 Fact Tables)

| Table | Partition Column | Local Sort Column |
|-------|-----------------|-------------------|
| store_sales | `ss_sold_date_sk` | `ss_item_sk` |
| catalog_sales | `cs_sold_date_sk` | `cs_item_sk` |
| web_sales | `ws_sold_date_sk` | `ws_item_sk` |
| store_returns | `sr_returned_date_sk` | `sr_item_sk` |
| catalog_returns | `cr_returned_date_sk` | `cr_item_sk` |
| web_returns | `wr_returned_date_sk` | `wr_item_sk` |
| inventory | `inv_date_sk` | `inv_item_sk` |

Iceberg table creation syntax:
```sql
CREATE TABLE "pedros nessie"."sample_1Tb"."store_sales"
PARTITION BY (ss_sold_date_sk) LOCALSORT BY (ss_item_sk) AS
SELECT ...
FROM tpcds."sample_1Tb"."store_sales"
```

#### Non-Partitioned Tables (18 Dimension Tables)

| Table | Column Count |
|-------|--------------|
| call_center | 31 |
| catalog_page | 9 |
| customer | 18 |
| customer_address | 13 |
| customer_demographics | 9 |
| date_dim | 28 |
| dbgen_version | 4 |
| household_demographics | 5 |
| income_band | 3 |
| item | 22 |
| promotion | 19 |
| reason | 3 |
| ship_mode | 6 |
| store | 29 |
| time_dim | 10 |
| warehouse | 14 |
| web_page | 14 |
| web_site | 26 |

---

## Column Mapping

The source Parquet files have generic column names (`_c0`, `_c1`, `_c2`, etc.). During Iceberg table creation, columns are renamed to proper TPC-DS schema names.

Example mapping for `reason` table:
```sql
SELECT
    _c0 as r_reason_sk,
    _c1 as r_reason_id,
    _c2 as r_reason_desc
FROM tpcds."sample_1Tb"."reason"
```

The full schema definitions are in [iceberg-kit/tpcds_schema.json](iceberg-kit/tpcds_schema.json).

---

## Deployment Script

### Configuration

Environment variables (`.env` file):

```bash
# S3 Configuration
S3_ENDPOINT_URL=http://compute-1.min.dc:30001
S3_ACCESS_KEY=<access_key>
S3_SECRET_KEY=<secret_key>
S3_BUCKET_NAME=tpcds
S3_FOLDER_NAME=sample_1Tb

# Iceberg Storage
ICEBERG_BUCKET_NAME=iceberg
ICEBERG_FOLDER_NAME=sample_1Tb

# Dremio Configuration
DREMIO_USERNAME=<username>
DREMIO_PASSWORD=<password>
DREMIO_URL=http://dremio-dremio-v26.apps.k2.min.dc/

# Dremio Source Names
DREMIO_SOURCE_NAME=tpcds
NESSIE_SOURCE_NAME=pedros nessie
```

### Usage

Deploy all tables:
```bash
cd iceberg-kit
python deploy_tables.py
```

Deploy a single table:
```bash
python deploy_tables.py --table store_sales
```

Promote folders only (without creating Iceberg tables):
```bash
python deploy_tables.py --promote-only
```

---

## Notes

### SQL Quoting
Folder names are quoted in SQL queries to handle names starting with numbers (e.g., `1Tb_512Mb_partition`):
```sql
SELECT * FROM tpcds."1Tb_512Mb_partition"."reason"
```

### Folder Promotion
Before querying Parquet data in Dremio, folders must be "promoted" to datasets. The deployment script handles this automatically via the Dremio Catalog API.

### Idempotency
The script checks if tables already exist before creating them, making it safe to re-run.
