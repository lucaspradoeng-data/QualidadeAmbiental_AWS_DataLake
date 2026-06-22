import time
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from qa_datalake.athena_sql import count_partition_sql, insert_curated_sql
from qa_datalake.config import Settings
from qa_datalake.csv_contract import ValidationSummary, validate_csv


class PipelineError(RuntimeError):
    pass


@dataclass(frozen=True)
class PipelineResult:
    s3_uri: str
    raw_rows: int
    curated_rows: int
    validation: ValidationSummary

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["validation"] = self.validation.to_dict()
        return result


class AwsPipeline:
    def __init__(
        self,
        settings: Settings,
        *,
        s3_client: Any,
        glue_client: Any,
        athena_client: Any,
    ) -> None:
        self.settings = settings
        self.s3 = s3_client
        self.glue = glue_client
        self.athena = athena_client

    @classmethod
    def from_settings(cls, settings: Settings) -> "AwsPipeline":
        import boto3

        session = boto3.Session(region_name=settings.region)
        return cls(
            settings,
            s3_client=session.client("s3"),
            glue_client=session.client("glue"),
            athena_client=session.client("athena"),
        )

    def ingest(
        self,
        csv_path: Path,
        ingestion_date: str,
        *,
        require_baseline: bool = False,
    ) -> PipelineResult:
        partition = date.fromisoformat(ingestion_date).isoformat()
        summary = validate_csv(csv_path, require_baseline=require_baseline)

        curated_before = self._partition_count(
            self.settings.curated_database,
            self.settings.curated_table,
            partition,
        )
        if curated_before:
            raise PipelineError(
                f"A particao {partition} ja possui {curated_before} registros na camada curated."
            )

        partition_prefix = (
            f"{self.settings.raw_prefix}/ingestion_date={partition}/"
        )
        existing = self.s3.list_objects_v2(
            Bucket=self.settings.bucket,
            Prefix=partition_prefix,
            MaxKeys=1,
        )
        if existing.get("KeyCount", 0):
            raise PipelineError(
                f"A particao raw s3://{self.settings.bucket}/{partition_prefix} nao esta vazia."
            )

        key = f"{partition_prefix}{csv_path.name}"
        self.s3.upload_file(
            str(csv_path),
            self.settings.bucket,
            key,
            ExtraArgs={"ContentType": "text/csv", "ServerSideEncryption": "AES256"},
        )

        self._run_crawler()
        raw_rows = self._partition_count(
            self.settings.raw_database,
            self.settings.raw_table,
            partition,
        )
        if raw_rows != summary.rows:
            raise PipelineError(
                f"Contagem raw divergente: CSV={summary.rows}, Athena={raw_rows}. "
                "A carga curated nao foi iniciada."
            )

        insert_sql = insert_curated_sql(
            raw_database=self.settings.raw_database,
            raw_table=self.settings.raw_table,
            curated_database=self.settings.curated_database,
            curated_table=self.settings.curated_table,
            ingestion_date=partition,
        )
        self._execute_athena(insert_sql)

        curated_rows = self._partition_count(
            self.settings.curated_database,
            self.settings.curated_table,
            partition,
        )
        if curated_rows != summary.rows:
            raise PipelineError(
                f"Contagem curated divergente: CSV={summary.rows}, Athena={curated_rows}."
            )

        return PipelineResult(
            s3_uri=f"s3://{self.settings.bucket}/{key}",
            raw_rows=raw_rows,
            curated_rows=curated_rows,
            validation=summary,
        )

    def _run_crawler(self) -> None:
        before = self.glue.get_crawler(Name=self.settings.crawler)["Crawler"]
        previous_start = before.get("LastCrawl", {}).get("StartTime")
        self.glue.start_crawler(Name=self.settings.crawler)
        deadline = time.monotonic() + self.settings.timeout_seconds
        observed_running = False

        while time.monotonic() < deadline:
            crawler = self.glue.get_crawler(Name=self.settings.crawler)["Crawler"]
            if crawler["State"] == "RUNNING":
                observed_running = True
                time.sleep(self.settings.poll_seconds)
                continue

            if crawler["State"] == "READY":
                last_crawl = crawler.get("LastCrawl", {})
                current_start = last_crawl.get("StartTime")
                is_current_run = observed_running or current_start != previous_start
                if not is_current_run:
                    time.sleep(self.settings.poll_seconds)
                    continue

                status = last_crawl.get("Status")
                if status == "SUCCEEDED":
                    return
                if status in {"FAILED", "CANCELLED"}:
                    message = last_crawl.get("ErrorMessage", status)
                    raise PipelineError(f"Crawler terminou com erro: {message}")
            time.sleep(self.settings.poll_seconds)

        raise PipelineError("Tempo limite excedido aguardando o Glue Crawler.")

    def _partition_count(self, database: str, table: str, partition: str) -> int:
        query = count_partition_sql(database, table, partition)
        query_id = self._execute_athena(query)
        response = self.athena.get_query_results(QueryExecutionId=query_id)
        rows = response["ResultSet"]["Rows"]
        if len(rows) < 2:
            raise PipelineError("Athena nao retornou a contagem esperada.")
        return int(rows[1]["Data"][0]["VarCharValue"])

    def _execute_athena(self, query: str) -> str:
        response = self.athena.start_query_execution(
            QueryString=query,
            WorkGroup=self.settings.workgroup,
        )
        query_id = response["QueryExecutionId"]
        deadline = time.monotonic() + self.settings.timeout_seconds

        while time.monotonic() < deadline:
            execution = self.athena.get_query_execution(QueryExecutionId=query_id)
            status = execution["QueryExecution"]["Status"]
            state = status["State"]
            if state == "SUCCEEDED":
                return query_id
            if state in {"FAILED", "CANCELLED"}:
                reason = status.get("StateChangeReason", state)
                raise PipelineError(f"Consulta Athena {query_id} terminou com erro: {reason}")
            time.sleep(self.settings.poll_seconds)

        raise PipelineError(f"Tempo limite excedido aguardando a consulta Athena {query_id}.")
