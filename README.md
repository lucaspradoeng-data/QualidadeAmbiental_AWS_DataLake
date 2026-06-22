<div align="center">

# 🌊 QualidadeAmbiental AWS Data Lake

**Contract-driven cloud ingestion pipeline for environmental water quality monitoring data.**

*From SQL Server to Parquet — validated, cataloged, and ready for Power BI.*

---

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![AWS](https://img.shields.io/badge/AWS-Cloud-FF9900?style=flat-square&logo=amazonaws&logoColor=white)](https://aws.amazon.com/)
[![Amazon S3](https://img.shields.io/badge/Amazon_S3-Storage-569A31?style=flat-square&logo=amazons3&logoColor=white)](https://aws.amazon.com/s3/)
[![AWS Glue](https://img.shields.io/badge/AWS_Glue-ETL-8C4FFF?style=flat-square&logo=awslambda&logoColor=white)](https://aws.amazon.com/glue/)
[![Amazon Athena](https://img.shields.io/badge/Amazon_Athena-Query-232F3E?style=flat-square&logo=amazonaws&logoColor=white)](https://aws.amazon.com/athena/)
[![Power BI](https://img.shields.io/badge/Power_BI-Reporting-F2C811?style=flat-square&logo=powerbi&logoColor=black)](https://powerbi.microsoft.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](./LICENSE)
[![Version](https://img.shields.io/badge/Version-0.1.0-blue?style=flat-square)]()
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen?style=flat-square)]()

</div>

---

## 📖 Sobre o Projeto

**QualidadeAmbiental AWS Data Lake** é um pipeline de engenharia de dados cloud-native derivado do contrato externo de dados v2.1.0 do projeto [`QualidadeAmbiental_SQLServer`](https://github.com/engambientalucas-design/QualidadeAmbiental_SQLServer). Ele automatiza a ingestão, validação, catalogação e transformação de dados de monitoramento de qualidade da água e esgoto em um Data Lake na AWS.

**Valor técnico:** O projeto implementa um pipeline de dados com contrato rígido de 30 colunas, validação local pré-ingestão, arquitetura medallion (raw → curated) e exposição analítica via Athena + Power BI — tudo sem armazenar credenciais no repositório.

**Valor de negócio:** Permite que engenheiros ambientais e analistas de dados acessem dados históricos de conformidade hídrica de forma confiável, rastreável e escalável, diretamente em ferramentas de BI corporativo.

> **Escopo v0.1.0:** Automação de validação e ingestão de novos lotes após o provisionamento da infraestrutura AWS. Provisionamento de infraestrutura e substituição destrutiva de partições estão fora do escopo desta versão.

---

## 🏗️ Arquitetura

```text
┌─────────────────────────────────────┐
│   SQL Server View / CSV Contratado  │
│          (Fonte de dados)           │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│    Python — Validação de Contrato   │
│  30 colunas · ISO dates · unicidade │
│  flags de conformidade · nulos      │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│         S3 Raw Zone (CSV)           │
│   Partição: /ingestion_date=YYYY-   │
│   MM-DD/                            │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│   AWS Glue Crawler + Data Catalog   │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│    Amazon Athena INSERT INTO        │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│      S3 Curated Zone (Parquet)      │
│         Compressão: Snappy          │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│    Amazon Athena → Power BI Import  │
│         (Camada analítica)          │
└─────────────────────────────────────┘
```

---

## 🎬 Demonstração

> **📌 Placeholder:** Adicione aqui um GIF ou vídeo do pipeline em execução — por exemplo, a saída do terminal ao rodar `qa-datalake ingest` com validação, upload para S3, e confirmação de contagem no Athena.

```
[ GIF / Screencast do pipeline aqui ]
Sugestão: grave com asciinema ou OBS e converta para GIF via gifski.
```

---

## ✨ Principais Funcionalidades

- **Validação de contrato pré-ingestão** — garante 30 colunas, tipos ISO, decimais, identifiers, unicidade e flags de conformidade antes de qualquer chamada à AWS.
- **Arquitetura medallion com S3** — zonas raw (CSV) e curated (Parquet/Snappy), particionadas por `ingestion_date`.
- **Proteção contra ingestão duplicada** — partições existentes em raw ou curated são rejeitadas automaticamente.
- **Contagem dupla de integridade** — a contagem Athena raw deve igualar a contagem local antes de carregar curated; após o carregamento, a contagem curated também deve igualar.
- **CLI ergonômica** — comandos `normalize`, `validate`, `plan` e `ingest` com flags claras.
- **Credenciais zero no repositório** — resolução exclusiva via AWS SDK credential chain (IAM Identity Center, perfil CLI ou variáveis de ambiente).
- **Suite de testes independente de nuvem** — sem dependências de AWS; roda com `unittest` puro.
- **Baseline reproduzível** — lote didático v2.1.0 com contagens verificadas para onboarding e CI.

---

## 🔢 Baseline Validado

O lote didático v2.1.0 é mantido como amostra reproduzível e deve retornar exatamente:

| Indicador | Valor |
|---|---:|
| Resultados analíticos | 72 |
| Resultados com limite de referência | 57 |
| Resultados sem limite de referência | 15 |
| Resultados conformes com limite | 50 |
| Resultados não-conformes com limite | 7 |

> O baseline é explícito e opcional. Lotes válidos futuros podem ter totais diferentes.

---

## 🛡️ Propriedades de Segurança

| Propriedade | Garantia |
|---|---|
| Validação local | Executa **antes** de qualquer chamada à AWS |
| Contrato rígido | Exatamente 30 colunas obrigatórias |
| Tipos validados | ISO dates, decimais, identifiers, nulos, unicidade, flags |
| Anti-duplicata | Partições existentes (raw ou curated) são rejeitadas |
| Integridade raw | Contagem Athena raw = contagem local CSV antes do curated |
| Integridade curated | Contagem Athena curated = contagem local CSV após carga |
| Sem sobrescrita | Nenhuma opção `--force` ou `--overwrite` exposta |
| Credenciais | Resolvidas pelo AWS SDK chain; nunca armazenadas no projeto |

---

## ⚙️ Pré-requisitos

Certifique-se de ter os itens abaixo instalados e configurados:

- **Python** `>= 3.11`
- **AWS CLI** configurado com um perfil IAM Identity Center (ou equivalente)
- **Acesso AWS** com permissões para S3, Glue, e Athena nos recursos declarados no `.env`
- Infraestrutura AWS já provisionada (buckets S3, Glue Crawler, banco de dados Athena)

---

## 🚀 Instalação

**1. Clone o repositório**

```bash
git clone https://github.com/engambientalucas-design/QualidadeAmbiental_AWSDataLake.git
cd QualidadeAmbiental_AWSDataLake
```

**2. Crie e ative o ambiente virtual**

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows
```

**3. Instale o pacote com dependências de desenvolvimento**

```bash
pip install -e ".[dev]"
```

**4. Configure as variáveis de ambiente**

```bash
cp .env.example .env
# Abra .env e preencha apenas os nomes dos recursos AWS.
# NÃO coloque Access Keys no .env — use um perfil AWS CLI.
```

---

## 📦 Configuração

Copie `.env.example` para `.env` e preencha os nomes dos seus recursos:

```dotenv
# .env — apenas nomes de recursos, sem segredos
QA_S3_RAW_BUCKET=meu-bucket-raw
QA_S3_CURATED_BUCKET=meu-bucket-curated
QA_GLUE_DATABASE=qualidade_ambiental
QA_ATHENA_OUTPUT_LOCATION=s3://meu-bucket-athena-results/
```

> Para desenvolvimento local, prefira um perfil AWS CLI com IAM Identity Center.
> A identidade IAM restrita do Power BI **não** é uma identidade de ingestão.

---

## 💻 Exemplos de Uso

**Normalizar um export bruto do SSMS:**

```bash
qa-datalake normalize data/input/export_ssms.csv data/output/dados_conformidade.csv
```

**Validar contra o baseline didático v2.1.0:**

```bash
qa-datalake validate data/sample/dados_conformidade_v2_1_0.csv --baseline
```

**Simular (dry-run) uma ingestão sem escrever na AWS:**

```bash
qa-datalake plan data/sample/dados_conformidade_v2_1_0.csv --ingestion-date 2026-06-22
```

**Ingerir um novo lote:**

```bash
qa-datalake ingest data/output/dados_conformidade.csv --ingestion-date 2026-07-01
```

> ⚠️ **Não execute** a ingestão de amostra contra `2026-06-22`: essa partição já existe no ambiente validado e o pipeline irá rejeitá-la corretamente.

---

## 🧪 Testes

Execute a suite de testes sem dependências de nuvem:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Os testes cobrem validação de contrato e geração de SQL. Nenhuma credencial ou chamada AWS é necessária.

---

## 🗂️ Estrutura do Projeto

```text
QualidadeAmbiental_AWSDataLake/
│
├── src/
│   └── qa_datalake/          # Pacote Python e CLI (normalize, validate, plan, ingest)
│
├── tests/                    # Suite de testes de contrato e geração SQL
│
├── docs/
│   └── runbook.md            # Procedimento de operação em lote e recuperação
│
├── data/
│   └── sample/               # Dataset didático contratado (v2.1.0)
│
├── .env.example              # Configuração de nomes de recursos sem segredos
├── pyproject.toml
└── README.md
```

---

## 🛠️ Stack Utilizada

| Camada | Tecnologia |
|---|---|
| ![Python](https://img.shields.io/badge/-Python_3.11+-3776AB?style=flat-square&logo=python&logoColor=white) | Linguagem principal, CLI, validação de contrato |
| ![Amazon S3](https://img.shields.io/badge/-Amazon_S3-569A31?style=flat-square&logo=amazons3&logoColor=white) | Armazenamento raw (CSV) e curated (Parquet/Snappy) |
| ![AWS Glue](https://img.shields.io/badge/-AWS_Glue-8C4FFF?style=flat-square&logo=awslambda&logoColor=white) | Crawler e Data Catalog |
| ![Amazon Athena](https://img.shields.io/badge/-Amazon_Athena-232F3E?style=flat-square&logo=amazonaws&logoColor=white) | Queries SQL serverless sobre S3 |
| ![Power BI](https://img.shields.io/badge/-Power_BI-F2C811?style=flat-square&logo=powerbi&logoColor=black) | Camada de relatórios e BI |
| ![SQL Server](https://img.shields.io/badge/-SQL_Server-CC2927?style=flat-square&logo=microsoftsqlserver&logoColor=white) | Fonte de dados (projeto externo contratado) |

---

## 🗺️ Roadmap

> Acompanhe o progresso via [GitHub Issues](../../issues).

- [x] Validação de contrato local (30 colunas, tipos, unicidade)
- [x] Ingestão raw para S3 com particionamento por `ingestion_date`
- [x] Catalogação via AWS Glue Crawler
- [x] Transformação raw → curated (Parquet/Snappy via Athena)
- [x] Suite de testes independente de nuvem
- [ ] Orquestração automática de lotes (ex: AWS Step Functions ou Airflow)
- [ ] Provisionamento de infraestrutura como código (Terraform / CDK)
- [ ] Monitoramento e alertas de qualidade de dados (ex: AWS CloudWatch)
- [ ] Suporte a múltiplas ETAs e sistemas de abastecimento
- [ ] Dashboard Power BI publicado como template

---

## 🤝 Contribuição

Contribuições são bem-vindas! Para contribuir:

1. Faça um **fork** do repositório
2. Crie uma branch descritiva: `git checkout -b feat/nome-da-feature`
3. Faça suas alterações e adicione testes quando aplicável
4. Certifique-se de que `python -m unittest discover -s tests -v` passa sem erros
5. Abra um **Pull Request** com descrição clara da mudança e motivação

Para reportar bugs ou sugerir melhorias, abra uma [Issue](../../issues).

---

## 📄 Licença

Distribuído sob a licença **MIT**. Consulte o arquivo [`LICENSE`](./LICENSE) para mais detalhes.

---

<div align="center">

Desenvolvido por **Lucas** · Engenharia Ambiental & Engenharia de Dados

[![GitHub](https://img.shields.io/badge/GitHub-engambientalucas--design-181717?style=flat-square&logo=github)](https://github.com/engambientalucas-design)

</div>
