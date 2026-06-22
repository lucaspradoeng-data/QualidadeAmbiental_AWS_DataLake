import csv
import tempfile
import unittest
from pathlib import Path

from qa_datalake.contract import HEADERS
from qa_datalake.csv_contract import CsvContractError, normalize_export, validate_csv


def _record(result_id: int = 1) -> list[str]:
    values = {header: "texto" for header in HEADERS}
    values.update(
        {
            "id_resultado": str(result_id),
            "id_amostra": "1",
            "codigo_amostra": "QA-TESTE-001",
            "data_coleta": "2026-06-22",
            "hora_coleta": "08:10:00",
            "id_tipo_amostra": "1",
            "id_ponto_coleta": "1",
            "id_responsavel": "1",
            "id_status": "1",
            "id_parametro": str(result_id),
            "valor_resultado": "7.2",
            "data_analise": "2026-06-23",
            "id_limite": "1",
            "valor_minimo": "6.0",
            "valor_maximo": "9.0",
            "classificacao_resultado": "Conforme",
            "possui_limite_referencia": "1",
            "indicador_nao_conforme": "0",
        }
    )
    return [values[header] for header in HEADERS]


def _write(path: Path, rows: list[list[str]], *, header: bool = True) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";", lineterminator="\n")
        if header:
            writer.writerow(HEADERS)
        writer.writerows(rows)


class CsvContractTests(unittest.TestCase):
    def test_validate_valid_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "valid.csv"
            _write(path, [_record()])

            summary = validate_csv(path)

            self.assertEqual(summary.rows, 1)
            self.assertEqual(summary.columns, 30)
            self.assertEqual(summary.with_limit, 1)
            self.assertEqual(summary.conformant, 1)

    def test_rejects_duplicate_result_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.csv"
            second = _record()
            second[HEADERS.index("id_parametro")] = "2"
            _write(path, [_record(), second])

            with self.assertRaisesRegex(CsvContractError, "id_resultado duplicado"):
                validate_csv(path)

    def test_normalize_headerless_export_and_nulls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            target = Path(directory) / "target.csv"
            row = _record()
            row[HEADERS.index("metodo_analise")] = "NULL"
            _write(source, [row], header=False)

            count = normalize_export(source, target)
            summary = validate_csv(target)

            self.assertEqual(count, 1)
            self.assertEqual(summary.rows, 1)
            self.assertNotIn("NULL", target.read_text(encoding="utf-8"))

    def test_baseline_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "valid.csv"
            _write(path, [_record()])

            with self.assertRaisesRegex(CsvContractError, "Baseline divergente"):
                validate_csv(path, require_baseline=True)


if __name__ == "__main__":
    unittest.main()
