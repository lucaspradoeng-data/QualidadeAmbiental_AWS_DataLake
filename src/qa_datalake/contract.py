from dataclasses import dataclass


HEADERS = (
    "id_resultado",
    "id_amostra",
    "codigo_amostra",
    "data_coleta",
    "hora_coleta",
    "id_tipo_amostra",
    "tipo_amostra",
    "id_ponto_coleta",
    "ponto_coleta",
    "tipo_ponto",
    "municipio",
    "estado",
    "id_responsavel",
    "responsavel",
    "id_status",
    "status_amostra",
    "id_parametro",
    "parametro",
    "categoria_parametro",
    "valor_resultado",
    "unidade_medida",
    "data_analise",
    "metodo_analise",
    "id_limite",
    "valor_minimo",
    "valor_maximo",
    "referencia_normativa",
    "classificacao_resultado",
    "possui_limite_referencia",
    "indicador_nao_conforme",
)

REQUIRED_INTEGER_FIELDS = (
    "id_resultado",
    "id_amostra",
    "id_tipo_amostra",
    "id_ponto_coleta",
    "id_responsavel",
    "id_status",
    "id_parametro",
)
NULLABLE_INTEGER_FIELDS = ("id_limite", "indicador_nao_conforme")
REQUIRED_DECIMAL_FIELDS = ("valor_resultado",)
NULLABLE_DECIMAL_FIELDS = ("valor_minimo", "valor_maximo")


@dataclass(frozen=True)
class Baseline:
    rows: int = 72
    with_limit: int = 57
    without_limit: int = 15
    conformant: int = 50
    non_conformant: int = 7


BASELINE = Baseline()

