import csv
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from qa_datalake.contract import (
    BASELINE,
    HEADERS,
    NULLABLE_DECIMAL_FIELDS,
    NULLABLE_INTEGER_FIELDS,
    REQUIRED_DECIMAL_FIELDS,
    REQUIRED_INTEGER_FIELDS,
)


class CsvContractError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("CSV fora do contrato:\n- " + "\n- ".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class ValidationSummary:
    path: str
    rows: int
    columns: int
    unique_samples: int
    unique_parameters: int
    with_limit: int
    without_limit: int
    conformant: int
    non_conformant: int

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


def _is_null(value: str) -> bool:
    return value == ""


def normalize_export(source: Path, target: Path, *, overwrite: bool = False) -> int:
    if target.exists() and not overwrite:
        raise FileExistsError(f"O arquivo de destino ja existe: {target}")

    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle, delimiter=";"))

    if not rows:
        raise CsvContractError(["O arquivo de origem esta vazio."])

    has_header = tuple(rows[0]) == HEADERS
    data_rows = rows[1:] if has_header else rows
    width_errors = [
        f"Linha {line}: esperadas {len(HEADERS)} colunas, encontradas {len(row)}."
        for line, row in enumerate(data_rows, start=2 if has_header else 1)
        if len(row) != len(HEADERS)
    ]
    if width_errors:
        raise CsvContractError(width_errors)

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";", lineterminator="\n")
        writer.writerow(HEADERS)
        writer.writerows(
            [["" if value == "NULL" else value for value in row] for row in data_rows]
        )

    return len(data_rows)


def validate_csv(path: Path, *, require_baseline: bool = False) -> ValidationSummary:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle, delimiter=";"))

    if not rows:
        raise CsvContractError(["O arquivo esta vazio."])

    errors: list[str] = []
    if tuple(rows[0]) != HEADERS:
        errors.append("O cabecalho nao corresponde ao contrato oficial de 30 colunas.")
        raise CsvContractError(errors)

    data_rows = rows[1:]
    records: list[dict[str, str]] = []
    for line_number, row in enumerate(data_rows, start=2):
        if len(row) != len(HEADERS):
            errors.append(
                f"Linha {line_number}: esperadas {len(HEADERS)} colunas, encontradas {len(row)}."
            )
            continue
        if "NULL" in row:
            errors.append(f"Linha {line_number}: use campo vazio em vez do literal NULL.")
        records.append(dict(zip(HEADERS, row, strict=True)))

    for line_number, record in enumerate(records, start=2):
        try:
            for field in REQUIRED_INTEGER_FIELDS:
                int(record[field])
            for field in NULLABLE_INTEGER_FIELDS:
                if not _is_null(record[field]):
                    int(record[field])
            for field in REQUIRED_DECIMAL_FIELDS:
                Decimal(record[field])
            for field in NULLABLE_DECIMAL_FIELDS:
                if not _is_null(record[field]):
                    Decimal(record[field])
            date.fromisoformat(record["data_coleta"])
            date.fromisoformat(record["data_analise"])
            if not _is_null(record["hora_coleta"]):
                time.fromisoformat(record["hora_coleta"])
        except (ValueError, InvalidOperation) as exc:
            errors.append(f"Linha {line_number}: tipo de dado invalido ({exc}).")
            continue

        has_limit = record["possui_limite_referencia"]
        indicator = record["indicador_nao_conforme"]
        classification = record["classificacao_resultado"]
        if has_limit not in {"0", "1"}:
            errors.append(
                f"Linha {line_number}: possui_limite_referencia deve ser 0 ou 1."
            )
        elif has_limit == "0":
            no_limit_fields = (
                record["id_limite"],
                record["valor_minimo"],
                record["valor_maximo"],
            )
            if (
                indicator != ""
                or classification != "Sem limite de referencia"
                or any(no_limit_fields)
            ):
                errors.append(
                    f"Linha {line_number}: registro sem limite tem campos de referencia "
                    "inconsistentes."
                )
        elif indicator not in {"0", "1"}:
            errors.append(
                f"Linha {line_number}: indicador_nao_conforme deve ser 0 ou 1 "
                "quando ha limite."
            )
        elif record["id_limite"] == "":
            errors.append(f"Linha {line_number}: registro com limite exige id_limite.")
        elif indicator == "0" and classification != "Conforme":
            errors.append(
                f"Linha {line_number}: indicador conforme exige classificacao Conforme."
            )
        elif indicator == "1" and classification not in {
            "Acima do limite maximo",
            "Abaixo do limite minimo",
        }:
            errors.append(
                f"Linha {line_number}: indicador nao conforme tem classificacao invalida."
            )

    result_ids = Counter(record["id_resultado"] for record in records)
    result_duplicates = sorted(key for key, count in result_ids.items() if count > 1)
    if result_duplicates:
        errors.append(f"id_resultado duplicado: {result_duplicates}")

    sample_parameter = Counter(
        (record["id_amostra"], record["id_parametro"]) for record in records
    )
    pair_duplicates = sorted(key for key, count in sample_parameter.items() if count > 1)
    if pair_duplicates:
        errors.append(f"Pares id_amostra/id_parametro duplicados: {pair_duplicates}")

    with_limit = sum(record["possui_limite_referencia"] == "1" for record in records)
    without_limit = len(records) - with_limit
    conformant = sum(
        record["possui_limite_referencia"] == "1"
        and record["indicador_nao_conforme"] == "0"
        for record in records
    )
    non_conformant = sum(
        record["possui_limite_referencia"] == "1"
        and record["indicador_nao_conforme"] == "1"
        for record in records
    )

    summary = ValidationSummary(
        path=str(path),
        rows=len(records),
        columns=len(HEADERS),
        unique_samples=len({record["id_amostra"] for record in records}),
        unique_parameters=len({record["id_parametro"] for record in records}),
        with_limit=with_limit,
        without_limit=without_limit,
        conformant=conformant,
        non_conformant=non_conformant,
    )

    if require_baseline:
        actual = (
            summary.rows,
            summary.with_limit,
            summary.without_limit,
            summary.conformant,
            summary.non_conformant,
        )
        expected = (
            BASELINE.rows,
            BASELINE.with_limit,
            BASELINE.without_limit,
            BASELINE.conformant,
            BASELINE.non_conformant,
        )
        if actual != expected:
            errors.append(f"Baseline divergente: esperado {expected}, encontrado {actual}.")

    if errors:
        raise CsvContractError(errors)
    return summary
