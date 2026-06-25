# Operational runbook

## Purpose

This runbook covers a new batch after the AWS foundation already exists. It does not create
buckets, IAM identities, Glue databases, crawlers, Athena workgroups, or the initial curated
table.

## Preconditions

- Use the `qa-datalake-ingestion` AWS profile, which assumes the dedicated ingestion role.
- Keep the Power BI access key restricted to Power BI; do not reuse it for ingestion.
- Export `dbo.VW_ConformidadeResultados` according to the v2.1.0 data contract.
- Use a new ISO ingestion date for every batch.
- Keep the Glue crawler unscheduled and run it only through the pipeline.
- Export only records that were not loaded in an earlier ingestion partition.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

Fill `.env` with resource names only. AWS credentials must come from an AWS profile,
IAM Identity Center, environment variables supplied by the execution environment, or an
attached role. Never put access keys in `.env`.

The validated local profile chain is:

```text
qa-datalake-cli-source
    -> sts:AssumeRole
qa-datalake-ingestion
    -> qa-datalake-ingestion-role
```

Validate the temporary identity before a live run:

```powershell
aws sts get-caller-identity --profile qa-datalake-ingestion
```

The ARN must contain `assumed-role/qa-datalake-ingestion-role`.

## Windows SQL Server export

For a local SQL Server Express instance that uses a self-signed certificate, `sqlcmd -C`
trusts that local certificate while retaining the encrypted connection. Do not apply this
exception to a remote production database.

Export one incremental sample without a header:

```powershell
sqlcmd `
  -S "localhost\SQLEXPRESS" `
  -d "QualidadeAmbiental" `
  -E -C -b -W -h-1 -s ";" -w 65535 -f 65001 `
  -Q "SET NOCOUNT ON; SELECT * FROM dbo.VW_ConformidadeResultados WHERE IdAmostra = 7 ORDER BY IdResultado;" `
  -o "data\input\dados_conformidade_amostra_7_sem_cabecalho.csv"
```

Normalize and validate the incremental export without `--baseline`:

```powershell
qa-datalake normalize `
  data\input\dados_conformidade_amostra_7_sem_cabecalho.csv `
  data\output\dados_conformidade_incremental_2026_06_23.csv

qa-datalake validate data\output\dados_conformidade_incremental_2026_06_23.csv
```

## Batch flow

Normalize an SSMS export only when it has no header or contains literal `NULL` values:

```bash
qa-datalake normalize data/input/export_ssms.csv data/output/dados_conformidade.csv
```

Validate locally before any AWS call:

```bash
qa-datalake validate data/output/dados_conformidade.csv
```

Preview the destination:

```bash
qa-datalake plan data/output/dados_conformidade.csv --ingestion-date 2026-07-01
```

Run one new batch:

```bash
qa-datalake ingest data/output/dados_conformidade.csv --ingestion-date 2026-07-01
```

The pipeline fails closed when the raw or curated partition already exists. It does not
overwrite a partition and does not offer a force flag for cloud writes.

The first live automated batch was validated on `2026-06-23` with the following gates:

```text
local rows: 12
raw rows: 12
curated rows: 12
with reference limit: 10
without reference limit: 2
conformant: 8
non-conformant: 2
```

The raw object was stored as `text/csv` with SSE-S3 (`AES256`). Glue registered both
partitions, and the curated table uses `MapredParquetInputFormat` with `ParquetHiveSerDe`.

## Recovery rules

- Validation failure: correct the local export; nothing was sent to AWS.
- Existing partition: choose the correct new ingestion date; do not bypass the check.
- Crawler failure: inspect `LastCrawl.ErrorMessage`; the raw object remains for diagnosis.
- Raw count mismatch: do not run `INSERT INTO`; inspect the partition and CSV schema.
- Athena insert failure: inspect the query and S3 destination before retrying because Athena
  can leave orphaned files after failed writes.
- Curated count mismatch: stop Power BI refresh and investigate before another ingestion.

## Cost controls

- Each Athena query scans data and can incur a minimum billable amount.
- The workgroup cutoff remains the last line of defense, not a substitute for partition filters.
- Power BI stays in Import mode with manual refresh for this portfolio dataset.
- The crawler has no schedule.
- AWS Budgets alerts notify; they do not hard-stop spending.
