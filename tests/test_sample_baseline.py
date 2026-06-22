import unittest
from pathlib import Path

from qa_datalake.csv_contract import validate_csv


class SampleBaselineTests(unittest.TestCase):
    def test_versioned_sample_matches_official_baseline(self) -> None:
        sample = (
            Path(__file__).parents[1]
            / "data"
            / "sample"
            / "dados_conformidade_v2_1_0.csv"
        )

        summary = validate_csv(sample, require_baseline=True)

        self.assertEqual(summary.rows, 72)
        self.assertEqual(summary.with_limit, 57)
        self.assertEqual(summary.without_limit, 15)
        self.assertEqual(summary.conformant, 50)
        self.assertEqual(summary.non_conformant, 7)


if __name__ == "__main__":
    unittest.main()
