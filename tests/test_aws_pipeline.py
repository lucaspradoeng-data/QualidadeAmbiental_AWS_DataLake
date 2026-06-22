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

    def list_objects_v2(self, **kwargs) -> dict:
        self.list_request = kwargs
        return {"KeyCount": 0}

    def upload_file(self, *args, **kwargs) -> None:
        self.uploads.append((args, kwargs))


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


class AwsPipelineTests(unittest.TestCase):
    @patch("qa_datalake.aws_pipeline.time.sleep", return_value=None)
    def test_crawler_waits_for_current_execution(self, _sleep) -> None:
        settings = Settings(
            region="us-east-1",
            bucket="bucket",
            raw_prefix="raw/dados_conformidade",
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
        self.assertEqual(len(s3.uploads), 1)
        self.assertEqual(len(athena.queries), 4)
        self.assertIn("INSERT INTO", athena.queries[2][0])


if __name__ == "__main__":
    unittest.main()
