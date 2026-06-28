import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile

from qa_datalake.aws_pipeline import AwsPipeline
from qa_datalake.config import Settings
from test_csv_contract import _record, _write


class FakeGlue:
    def __init__(self) -> None:
        self.responses = iter(
            [
                {"State": "READY", "LastCrawl": {"Status": "SUCCEEDED", "StartTime": 1}},
                {"State": "READY", "LastCrawl": {"Status": "SUCCEEDED", "StartTime": 1}},
                {"State": "RUNNING", "LastCrawl": {"Status": "SUCCEEDED", "StartTime": 1}},
                {"State": "READY", "LastCrawl": {"Status": "SUCCEEDED", "StartTime": 2}},
            ]
        )
        self.start_calls = 0

    def get_crawler(self, *, Name: str) -> dict:
        assert Name == "crawler"
        return {"Crawler": next(self.responses)}

    def start_crawler(self, *, Name: str) -> None:
        assert Name == "crawler"
        self.start_calls += 1


class FakeS3:
    def __init__(self) -> None:
        self.uploads = []
        self.puts = []

    def list_objects_v2(self, **kwargs) -> dict:
        self.list_request = kwargs
        return {"KeyCount": 0}

    def upload_file(self, *args, **kwargs) -> None:
        self.uploads.append((args, kwargs))

    def put_object(self, **kwargs) -> dict:
        self.puts.append(kwargs)
        return {"ETag": '"manifest"'}


class FakeAthena:
    def __init__(self) -> None:
        self.queries = []
        self.counts = iter([0, 1, 1])

    def start_query_execution(self, *, QueryString: str, WorkGroup: str) -> dict:
        self.queries.append((QueryString, WorkGroup))
        return {"QueryExecutionId": f"q{len(self.queries)}"}

    def get_query_execution(self, *, QueryExecutionId: str) -> dict:
        return {"QueryExecution": {"Status": {"State": "SUCCEEDED"}}}

    def get_query_results(self, *, QueryExecutionId: str) -> dict:
        count = next(self.counts)
        return {
            "ResultSet": {
                "Rows": [
                    {"Data": [{"VarCharValue": "total"}]},
                    {"Data": [{"VarCharValue": str(count)}]},
                ]
            }
        }


class FakeSts:
    def get_caller_identity(self) -> dict:
        return {
            "Account": "123456789012",
            "Arn": "arn:aws:sts::123456789012:assumed-role/role/session",
            "UserId": "AROATEST:session",
        }


class AwsPipelineTests(unittest.TestCase):
    @patch("qa_datalake.aws_pipeline.time.sleep", return_value=None)
    def test_crawler_waits_for_current_execution(self, _sleep) -> None:
        settings = Settings(
            region="us-east-1",
            bucket="bucket",
            raw_prefix="raw/dados_conformidade",
            audit_prefix="audit/manifests",
            crawler="crawler",
            workgroup="workgroup",
            raw_database="raw_db",
            raw_table="raw_table",
            curated_database="curated_db",
            curated_table="curated_table",
            poll_seconds=1,
            timeout_seconds=60,
        )
        glue = FakeGlue()
        pipeline = AwsPipeline(
            settings,
            s3_client=object(),
            glue_client=glue,
            athena_client=object(),
        )

        pipeline._run_crawler()

        self.assertEqual(glue.start_calls, 1)

    @patch("qa_datalake.aws_pipeline.time.sleep", return_value=None)
    def test_complete_ingestion_flow(self, _sleep) -> None:
        settings = Settings(
            region="us-east-1",
            bucket="bucket",
            raw_prefix="raw/dados_conformidade",
            audit_prefix="audit/manifests",
            crawler="crawler",
            workgroup="workgroup",
            raw_database="raw_db",
            raw_table="raw_table",
            curated_database="curated_db",
            curated_table="curated_table",
            poll_seconds=1,
            timeout_seconds=60,
        )
        s3 = FakeS3()
        glue = FakeGlue()
        athena = FakeAthena()
        pipeline = AwsPipeline(
            settings,
            s3_client=s3,
            glue_client=glue,
            athena_client=athena,
            sts_client=FakeSts(),
        )

        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "batch.csv"
            _write(csv_path, [_record()])

            result = pipeline.ingest(csv_path, "2026-07-01")

        self.assertEqual(result.raw_rows, 1)
        self.assertEqual(result.curated_rows, 1)
        self.assertEqual(
            result.s3_uri,
            "s3://bucket/raw/dados_conformidade/ingestion_date=2026-07-01/batch.csv",
        )
        self.assertTrue(
            result.manifest_s3_uri.startswith(
                "s3://bucket/audit/manifests/ingestion_date=2026-07-01/ingest_"
            )
        )
        self.assertEqual(len(s3.uploads), 1)
        self.assertEqual(len(s3.puts), 1)
        self.assertEqual(s3.puts[0]["Bucket"], "bucket")
        self.assertTrue(
            s3.puts[0]["Key"].startswith(
                "audit/manifests/ingestion_date=2026-07-01/ingest_"
            )
        )
        self.assertEqual(s3.puts[0]["ContentType"], "application/json")
        self.assertEqual(s3.puts[0]["ServerSideEncryption"], "AES256")
        self.assertEqual(len(athena.queries), 4)
        self.assertIn("INSERT INTO", athena.queries[2][0])
        self.assertEqual(result.manifest["pipeline_version"], "0.4.0")
        self.assertEqual(result.manifest["status"], "success")
        self.assertEqual(result.manifest["ingestion_date"], "2026-07-01")
        self.assertEqual(result.manifest["manifest_s3_uri"], result.manifest_s3_uri)
        self.assertEqual(result.manifest["source_file"].endswith("batch.csv"), True)
        self.assertEqual(len(result.manifest["source_sha256"]), 64)
        self.assertEqual(result.manifest["raw_rows"], 1)
        self.assertEqual(result.manifest["curated_rows"], 1)
        self.assertEqual(
            result.manifest["athena_query_execution_ids"],
            {
                "curated_precheck": "q1",
                "raw_count": "q2",
                "insert_curated": "q3",
                "curated_count": "q4",
            },
        )
        self.assertEqual(
            result.manifest["aws_identity"]["arn"],
            "arn:aws:sts::123456789012:assumed-role/role/session",
        )
        self.assertIn("upload_raw", result.manifest["timings_seconds"])
        self.assertNotIn("upload_audit_manifest", result.manifest["timings_seconds"])


if __name__ == "__main__":
    unittest.main()
