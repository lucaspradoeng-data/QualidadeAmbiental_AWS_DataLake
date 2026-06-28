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
    target = manifest_dir / manifest_filename(manifest)
    target.write_bytes(manifest_json_bytes(manifest))
    return target


def manifest_filename(manifest: dict[str, Any]) -> str:
    ingestion_date = str(manifest["ingestion_date"])
    timestamp = str(manifest["finished_at"]).replace(":", "").replace("-", "")
    return f"ingest_{ingestion_date}_{timestamp}.json"


def manifest_json_bytes(manifest: dict[str, Any]) -> bytes:
    return (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
