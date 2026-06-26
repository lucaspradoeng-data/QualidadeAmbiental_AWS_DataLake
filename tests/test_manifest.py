import json
import tempfile
import unittest
from pathlib import Path

from qa_datalake.manifest import sha256_file, write_manifest


class ManifestTests(unittest.TestCase):
    def test_sha256_file_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.csv"
            path.write_bytes(b"a;b\n1;2\n")

            self.assertEqual(
                sha256_file(path),
                "403bea5152c251c5bc7ef420d824d191605723f99392e83a0549ad58c6d46291",
            )

    def test_write_manifest_creates_json_file(self) -> None:
        manifest = {
            "ingestion_date": "2026-07-01",
            "finished_at": "2026-07-01T10:20:30Z",
            "status": "success",
        }

        with tempfile.TemporaryDirectory() as directory:
            path = write_manifest(manifest, Path(directory))

            self.assertEqual(path.name, "ingest_2026-07-01_20260701T102030Z.json")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), manifest)


if __name__ == "__main__":
    unittest.main()
