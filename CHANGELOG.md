# Changelog

All notable changes to this project are documented in this file.

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

