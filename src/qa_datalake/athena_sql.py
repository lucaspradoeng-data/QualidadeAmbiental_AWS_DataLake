import re
from datetime import date

from qa_datalake.contract import HEADERS


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _qualified(database: str, table: str) -> str:
    for value in (database, table):
        if not _IDENTIFIER.fullmatch(value):
            raise ValueError(f"Identificador Athena invalido: {value}")
    return f'"{database}"."{table}"'


def _date_literal(ingestion_date: str) -> str:
    return date.fromisoformat(ingestion_date).isoformat()


def count_partition_sql(database: str, table: str, ingestion_date: str) -> str:
    qualified = _qualified(database, table)
    value = _date_literal(ingestion_date)
    return f"SELECT COUNT(*) AS total FROM {qualified} WHERE ingestion_date = '{value}'"


def insert_curated_sql(
    *,
    raw_database: str,
    raw_table: str,
    curated_database: str,
    curated_table: str,
    ingestion_date: str,
) -> str:
    raw = _qualified(raw_database, raw_table)
    curated = _qualified(curated_database, curated_table)
    value = _date_literal(ingestion_date)

    projections = list(HEADERS)
    projections[HEADERS.index("data_coleta")] = "CAST(data_coleta AS DATE) AS data_coleta"
    projections[HEADERS.index("data_analise")] = "CAST(data_analise AS DATE) AS data_analise"
    projections.append("ingestion_date")
    select_list = ",\n    ".join(projections)

    return (
        f"INSERT INTO {curated}\n"
        f"SELECT\n    {select_list}\n"
        f"FROM {raw}\n"
        f"WHERE ingestion_date = '{value}'"
    )

