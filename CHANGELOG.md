# Changelog

All notable changes to this project are documented in this file.

## [0.4.0] - 2026-06-28

### Added

- Cloud audit manifest upload to S3 after successful `ingest` runs.
- `QA_AUDIT_PREFIX` setting with default `audit/manifests`.
- `manifest_s3_uri` in pipeline and CLI output.
- Audit manifest S3 prefix in the least-privilege IAM template.

### Changed

- `plan` now shows the expected audit manifest S3 URI pattern.
- Project package version bumped to `0.4.0`.

## [0.3.0] - 2026-06-26

### Added

- Operational ingestion manifest written locally after successful `ingest` runs.
- SHA256 checksum for the source CSV loaded into S3 raw.
- Timings for the main ingestion stages.
- Athena `QueryExecutionId` tracking for count checks and curated insert.
- AWS caller identity capture through STS when available.
- Unit tests for manifest creation and pipeline evidence.

### Changed

- `ingest` output now includes `manifest_path` and an embedded operational manifest.
- Local generated manifests are ignored by Git through the `artifacts/` directory.
- Project package version bumped to `0.3.0`.

## [0.2.0] - 2026-06-23

### Added

- Dedicated IAM user-to-role authentication flow for local ingestion.
- Least-privilege IAM policy templates for S3, Glue, and Athena access.
- AWS named profile support through `AWS_PROFILE` in the environment template.
- First live incremental ingestion evidence: 12 raw rows and 12 curated rows.

### Changed

- CLI now reports expected validation and pipeline failures without a Python traceback.
- Operational runbook now documents the validated Windows export and live ingestion flow.

### Validated

- IAM source user denied direct S3 access as designed.
- Temporary STS session successfully assumed `qa-datalake-ingestion-role`.
- Raw CSV stored with SSE-S3 encryption.
- Glue registered raw and curated partitions for `2026-06-23`.
- Athena transformed the incremental batch into Parquet.
- Incremental metrics: `12 / 10 / 2 / 8 / 2`.

## [0.1.0] - 2026-06-22

### Added

- Standalone AWS data lake project boundary derived from the SQL Server v2.1.0 contract.
- CSV normalization and strict 30-column validation.
- Optional validation of the official `72 / 57 / 15 / 50 / 7` baseline.
- Partition-safe S3 upload flow.
- Glue crawler execution with current-run detection.
- Athena raw and curated count gates.
- Athena `INSERT INTO` generation for partitioned Parquet loading.
- Operational runbook, environment template, didactic sample, and dependency-free tests.
