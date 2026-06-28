import argparse
import json
import sys
from datetime import date
from pathlib import Path

from qa_datalake.aws_pipeline import AwsPipeline, PipelineError
from qa_datalake.config import Settings
from qa_datalake.csv_contract import CsvContractError, normalize_export, validate_csv
from qa_datalake.manifest import write_manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qa-datalake",
        description="Valida e ingere o contrato de dados Qualidade Ambiental na AWS.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    normalize = subcommands.add_parser(
        "normalize", help="Normaliza uma exportacao SSMS para o contrato CSV."
    )
    normalize.add_argument("source", type=Path)
    normalize.add_argument("target", type=Path)
    normalize.add_argument("--force", action="store_true")

    validate = subcommands.add_parser("validate", help="Valida o contrato CSV local.")
    validate.add_argument("csv", type=Path)
    validate.add_argument("--baseline", action="store_true")

    plan = subcommands.add_parser("plan", help="Mostra o destino S3 sem acessar a AWS.")
    plan.add_argument("csv", type=Path)
    plan.add_argument("--ingestion-date", default=date.today().isoformat())
    plan.add_argument("--baseline", action="store_true")

    ingest = subcommands.add_parser(
        "ingest", help="Executa validacao, upload, crawler e carga curated."
    )
    ingest.add_argument("csv", type=Path)
    ingest.add_argument("--ingestion-date", default=date.today().isoformat())
    ingest.add_argument("--baseline", action="store_true")
    ingest.add_argument(
        "--manifest-dir",
        type=Path,
        default=Path("artifacts/manifests"),
        help="Diretorio local onde o manifesto operacional sera gravado.",
    )
    return parser


def _run() -> None:
    args = _parser().parse_args()

    if args.command == "normalize":
        rows = normalize_export(args.source, args.target, overwrite=args.force)
        print(json.dumps({"target": str(args.target), "rows": rows}, indent=2))
        return

    if args.command == "validate":
        summary = validate_csv(args.csv, require_baseline=args.baseline)
        print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
        return

    settings = Settings.from_env()
    summary = validate_csv(args.csv, require_baseline=args.baseline)
    partition = date.fromisoformat(args.ingestion_date).isoformat()

    if args.command == "plan":
        key = f"{settings.raw_prefix}/ingestion_date={partition}/{args.csv.name}"
        manifest_key = (
            f"{settings.audit_prefix}/ingestion_date={partition}/"
            "ingest_<timestamp>.json"
        )
        print(
            json.dumps(
                {
                    "validation": summary.to_dict(),
                    "s3_uri": f"s3://{settings.bucket}/{key}",
                    "manifest_s3_uri_pattern": f"s3://{settings.bucket}/{manifest_key}",
                    "crawler": settings.crawler,
                    "workgroup": settings.workgroup,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    pipeline = AwsPipeline.from_settings(settings)
    result = pipeline.ingest(
        args.csv,
        partition,
        require_baseline=args.baseline,
    )
    manifest_path = write_manifest(result.manifest, args.manifest_dir)
    output = result.to_dict()
    output["manifest_path"] = str(manifest_path)
    print(json.dumps(output, ensure_ascii=False, indent=2))


def main() -> None:
    try:
        _run()
    except (CsvContractError, FileNotFoundError, PipelineError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
