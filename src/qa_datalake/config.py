import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> bool:
        return False


@dataclass(frozen=True)
class Settings:
    region: str
    bucket: str
    raw_prefix: str
    audit_prefix: str
    crawler: str
    workgroup: str
    raw_database: str
    raw_table: str
    curated_database: str
    curated_table: str
    poll_seconds: int
    timeout_seconds: int

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        bucket = os.getenv("QA_S3_BUCKET", "").strip()
        if not bucket or bucket == "replace-with-your-bucket-name":
            raise ValueError("Defina QA_S3_BUCKET no arquivo .env.")

        return cls(
            region=os.getenv("QA_AWS_REGION", "us-east-1"),
            bucket=bucket,
            raw_prefix=os.getenv("QA_RAW_PREFIX", "raw/dados_conformidade").strip("/"),
            audit_prefix=os.getenv("QA_AUDIT_PREFIX", "audit/manifests").strip("/"),
            crawler=os.getenv(
                "QA_GLUE_CRAWLER", "qa-dados-conformidade-raw-crawler"
            ),
            workgroup=os.getenv("QA_ATHENA_WORKGROUP", "qa-qualidade-ambiental-wg"),
            raw_database=os.getenv("QA_RAW_DATABASE", "qualidade_ambiental_raw"),
            raw_table=os.getenv("QA_RAW_TABLE", "raw_dados_conformidade"),
            curated_database=os.getenv(
                "QA_CURATED_DATABASE", "qualidade_ambiental_curated"
            ),
            curated_table=os.getenv("QA_CURATED_TABLE", "dados_conformidade"),
            poll_seconds=int(os.getenv("QA_POLL_SECONDS", "5")),
            timeout_seconds=int(os.getenv("QA_TIMEOUT_SECONDS", "600")),
        )
