import unittest

from qa_datalake.athena_sql import count_partition_sql, insert_curated_sql


class AthenaSqlTests(unittest.TestCase):
    def test_count_partition_sql(self) -> None:
        query = count_partition_sql("curated_db", "results", "2026-06-22")

        self.assertIn('FROM "curated_db"."results"', query)
        self.assertIn("ingestion_date = '2026-06-22'", query)

    def test_insert_keeps_partition_column_last(self) -> None:
        query = insert_curated_sql(
            raw_database="raw_db",
            raw_table="raw_results",
            curated_database="curated_db",
            curated_table="results",
            ingestion_date="2026-06-22",
        )

        select_block = query.split("FROM", maxsplit=1)[0]
        self.assertIn("CAST(data_coleta AS DATE) AS data_coleta", select_block)
        self.assertIn("CAST(data_analise AS DATE) AS data_analise", select_block)
        self.assertTrue(select_block.rstrip().endswith("ingestion_date"))

    def test_rejects_unsafe_identifier(self) -> None:
        with self.assertRaisesRegex(ValueError, "Identificador Athena invalido"):
            count_partition_sql("db;drop", "results", "2026-06-22")

    def test_rejects_invalid_ingestion_date(self) -> None:
        with self.assertRaises(ValueError):
            count_partition_sql("db", "results", "22-06-2026")


if __name__ == "__main__":
    unittest.main()
