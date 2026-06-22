# ADR 0001: Keep AWS Data Lake automation in a derived repository

- Status: Accepted
- Date: 2026-06-22

## Context

`QualidadeAmbiental_SQLServer` reached version 2.1.0 as a closed SQL Server portfolio project.
Its official data contract explicitly treats API, Power BI, DataOps, and cloud automation as
derived projects. Adding AWS runtime code to that repository would break the documented scope
boundary and mix database ownership with cloud operations.

## Decision

Maintain `QualidadeAmbiental_AWS_DataLake` as a separate repository. It consumes the contracted
CSV exported from `dbo.VW_ConformidadeResultados` and owns:

- local contract validation;
- S3 raw ingestion;
- Glue catalog updates;
- Athena transformations;
- S3 curated data;
- operational automation for new batches.

The SQL Server repository remains the source of truth for relational modeling and conformance
classification. This repository does not recalculate that business rule.

## Consequences

- Both projects have clear ownership and independent versioning.
- The CSV contract is the integration boundary.
- Breaking contract changes require coordinated versions.
- AWS credentials, account identifiers, and environment-specific resource names stay outside Git.

