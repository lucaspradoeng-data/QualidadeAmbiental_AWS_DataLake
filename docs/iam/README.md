# IAM templates

These templates document the least-privilege identity flow validated for local ingestion:

```text
qa-datalake-cli
    -> sts:AssumeRole
qa-datalake-ingestion-role
    -> S3, Glue, and Athena project resources
```

Replace `${AWS_ACCOUNT_ID}` and `${BUCKET_NAME}` before applying a template. The files do not
contain access keys, secret keys, session tokens, or other credentials.

The source user has no direct data access. Its only permission is assuming the ingestion role.
The ingestion role does not allow deleting S3 objects or administering Glue and Athena resources.
For ingestion auditability, the role can write JSON manifests only under the project audit prefix:
`audit/manifests/*`.
