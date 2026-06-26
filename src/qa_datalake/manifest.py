import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


def isoformat_utc(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(manifest: dict[str, Any], manifest_dir: Path) -> Path:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    ingestion_date = str(manifest["ingestion_date"])
    timestamp = str(manifest["finished_at"]).replace(":", "").replace("-", "")
    target = manifest_dir / f"ingest_{ingestion_date}_{timestamp}.json"
    target.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target
