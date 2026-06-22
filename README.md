# Qualidade Ambiental AWS Data Lake

Derived cloud data engineering project based on the official v2.1.0 external data contract
from [`QualidadeAmbiental_SQLServer`](https://github.com/engambientalucas-design/QualidadeAmbiental_SQLServer).
The source repository remains a closed SQL Server portfolio project; this repository owns AWS
ingestion, validation, cataloging, transformation, and operational automation.

## Architecture

```text
SQL Server view / contracted CSV
              |
              v
Python contract validation
              |
              v
S3 raw (CSV, ingestion_date partition)
              |
              v
AWS Glue Crawler + Data Catalog
              |
              v
Amazon Athena INSERT INTO
              |
              v
S3 curated (Parquet/Snappy)
              |
              v
Amazon Athena -> Power BI Import
```

## Validated baseline

The didactic v2.1.0 batch is kept as a reproducible sample and must return:

| Indicator | Value |
| --- | ---: |
| Analytical results | 72 |
| Results with a reference limit | 57 |
| Results without a reference limit | 15 |
| Conformant results with a limit | 50 |
| Non-conformant results with a limit | 7 |

The baseline is explicit and optional. Future valid batches are allowed to have different totals.

## Safety properties

- Local validation runs before any AWS API call.
- The exact 30-column contract is enforced.
- ISO dates, decimals, identifiers, null representation, uniqueness, and conformance flags are
  validated.
- Existing raw or curated partitions are rejected to prevent duplicate ingestion.
- The raw Athena count must equal the local CSV count before curated loading.
- The curated Athena count must equal the local CSV count after loading.
- Cloud writes have no force or overwrite option.
- Credentials are resolved by the standard AWS SDK chain and are never stored in the project.

## Commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

qa-datalake normalize data/input/export_ssms.csv data/output/dados_conformidade.csv
qa-datalake validate data/sample/dados_conformidade_v2_1_0.csv --baseline
qa-datalake plan data/sample/dados_conformidade_v2_1_0.csv --ingestion-date 2026-06-22
qa-datalake ingest data/output/dados_conformidade.csv --ingestion-date 2026-07-01
```

Run the dependency-free test suite with:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Do not execute the sample ingestion against `2026-06-22`: that partition already exists in the
validated environment, and the pipeline will correctly reject it.

## Configuration

Copy `.env.example` to `.env` and fill only resource names. Do not put AWS access keys in `.env`.
For local development, prefer an AWS CLI profile backed by IAM Identity Center. The restricted
Power BI IAM identity is not an ingestion identity.

## Project structure

```text
src/qa_datalake/       Python package and CLI
tests/                 Contract and SQL generation tests
docs/runbook.md        Batch operation and recovery procedure
data/sample/           Small didactic contracted dataset
.env.example           Resource-name configuration without secrets
```

## Current scope

Version `0.1.0` automates new batch validation and ingestion after the AWS foundation has been
created. Infrastructure provisioning and destructive partition replacement are intentionally out
of scope for this version.

The reference limits and results are didactic. They do not constitute regulatory or legal
classification without specific technical and normative validation.
