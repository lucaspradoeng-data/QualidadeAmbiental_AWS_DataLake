import time
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from qa_datalake.athena_sql import count_partition_sql, insert_curated_sql
from qa_datalake.config import Settings
from qa_datalake.csv_contract import ValidationSummary, validate_csv
from qa_datalake.manifest import (
    isoformat_utc,
    manifest_filename,
    manifest_json_bytes,
    sha256_file,
    utc_now,
)


class PipelineError(RuntimeError):
    pass


@dataclass(frozen=True)
class PipelineResult:
    s3_uri: str
    manifest_s3_uri: str
    raw_rows: int
    curated_rows: int
    validation: ValidationSummary
    manifest: dict[str, Any]

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
        sts_client: Any | None = None,
    ) -> None:
        self.settings = settings
        self.s3 = s3_client
        self.glue = glue_client
        self.athena = athena_client
        self.sts = sts_client

    @classmethod
    def from_settings(cls, settings: Settings) -> "AwsPipeline":
        import boto3

        session = boto3.Session(region_name=settings.region)
        return cls(
            settings,
            s3_client=session.client("s3"),
            glue_client=session.client("glue"),
            athena_client=session.client("athena"),
            sts_client=session.client("sts"),
        )

    def ingest(
        self,
        csv_path: Path,
        ingestion_date: str,
        *,
        require_baseline: bool = False,
    ) -> PipelineResult:
        started_at = utc_now()
        started_monotonic = time.monotonic()
        timings: dict[str, float] = {}
        query_ids: dict[str, str] = {}
        partition = date.fromisoformat(ingestion_date).isoformat()
        source_sha256 = sha256_file(csv_path)
        summary = self._timed(
            "validate_csv",
            timings,
            lambda: validate_csv(csv_path, require_baseline=require_baseline),
        )

        curated_before = self._timed(
            "curated_precheck",
            timings,
            lambda: self._partition_count(
                self.settings.curated_database,
                self.settings.curated_table,
                partition,
                query_ids=query_ids,
                query_name="curated_precheck",
            ),
        )
        if curated_before:
            raise PipelineError(
                f"A particao {partition} ja possui {curated_before} registros na camada curated."
            )

        partition_prefix = (
            f"{self.settings.raw_prefix}/ingestion_date={partition}/"
        )
        existing = self._timed(
            "raw_precheck",
            timings,
            lambda: self.s3.list_objects_v2(
                Bucket=self.settings.bucket,
                Prefix=partition_prefix,
                MaxKeys=1,
            ),
        )
        if existing.get("KeyCount", 0):
            raise PipelineError(
                f"A particao raw s3://{self.settings.bucket}/{partition_prefix} nao esta vazia."
            )

        key = f"{partition_prefix}{csv_path.name}"
        self._timed(
            "upload_raw",
            timings,
            lambda: self.s3.upload_file(
                str(csv_path),
                self.settings.bucket,
                key,
                ExtraArgs={"ContentType": "text/csv", "ServerSideEncryption": "AES256"},
            ),
        )

        self._timed("run_crawler", timings, self._run_crawler)
        raw_rows = self._timed(
            "raw_count",
            timings,
            lambda: self._partition_count(
                self.settings.raw_database,
                self.settings.raw_table,
                partition,
                query_ids=query_ids,
                query_name="raw_count",
            ),
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
        query_ids["insert_curated"] = self._timed(
            "insert_curated",
            timings,
            lambda: self._execute_athena(insert_sql),
        )

        curated_rows = self._timed(
            "curated_count",
            timings,
            lambda: self._partition_count(
                self.settings.curated_database,
                self.settings.curated_table,
                partition,
                query_ids=query_ids,
                query_name="curated_count",
            ),
        )
        if curated_rows != summary.rows:
            raise PipelineError(
                f"Contagem curated divergente: CSV={summary.rows}, Athena={curated_rows}."
            )
        finished_at = utc_now()
        duration_seconds = round(time.monotonic() - started_monotonic, 3)
        manifest = {
            "pipeline_version": "0.4.0",
            "command": "ingest",
            "status": "success",
            "ingestion_date": partition,
            "source_file": str(csv_path),
            "source_sha256": source_sha256,
            "s3_uri": f"s3://{self.settings.bucket}/{key}",
            "raw_rows": raw_rows,
            "curated_rows": curated_rows,
            "validation": summary.to_dict(),
            "athena_query_execution_ids": query_ids,
            "aws_identity": self._aws_identity(),
            "timings_seconds": timings,
            "started_at": isoformat_utc(started_at),
            "finished_at": isoformat_utc(finished_at),
            "duration_seconds": duration_seconds,
        }
        manifest_key = (
            f"{self.settings.audit_prefix}/ingestion_date={partition}/"
            f"{manifest_filename(manifest)}"
        )
        manifest_s3_uri = f"s3://{self.settings.bucket}/{manifest_key}"
        manifest["manifest_s3_uri"] = manifest_s3_uri
        self.s3.put_object(
            Bucket=self.settings.bucket,
            Key=manifest_key,
            Body=manifest_json_bytes(manifest),
            ContentType="application/json",
            ServerSideEncryption="AES256",
        )

        return PipelineResult(
            s3_uri=f"s3://{self.settings.bucket}/{key}",
            manifest_s3_uri=manifest_s3_uri,
            raw_rows=raw_rows,
            curated_rows=curated_rows,
            validation=summary,
            manifest=manifest,
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

    def _partition_count(
        self,
        database: str,
        table: str,
        partition: str,
        *,
        query_ids: dict[str, str] | None = None,
        query_name: str | None = None,
    ) -> int:
        query = count_partition_sql(database, table, partition)
        query_id = self._execute_athena(query)
        if query_ids is not None and query_name is not None:
            query_ids[query_name] = query_id
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

    def _aws_identity(self) -> dict[str, str] | None:
        if self.sts is None:
            return None
        try:
            response = self.sts.get_caller_identity()
        except Exception as exc:
            return {"error": str(exc)}
        return {
            "account": response.get("Account", ""),
            "arn": response.get("Arn", ""),
            "user_id": response.get("UserId", ""),
        }

    def _timed(self, name: str, timings: dict[str, float], operation: Any) -> Any:
        started = time.monotonic()
        try:
            return operation()
        finally:
            timings[name] = round(time.monotonic() - started, 3)
