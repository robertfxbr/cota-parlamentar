"""As perguntas, escritas em SQL sobre a tabela limpa.

DuckDB consulta o Parquet direto, sem servidor e sem carregar tudo em memoria.
As consultas ficam aqui, em texto, e nao espalhadas por celulas de notebook:
assim da para ler o que foi perguntado sem executar nada.

Nenhuma consulta daqui ordena parlamentar por valor bruto entre estados. O
motivo esta no README: a cota mensal varia por UF porque embute passagem
aerea, entao "quem gastou mais" comparando Acre com Sao Paulo mede distancia
de Brasilia, nao comportamento.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Consulta:
    """Uma pergunta, com o SQL que a responde e a ressalva que ela exige."""

    nome: str
    pergunta: str
    sql: str
    ressalva: str = ""


CONSULTAS: tuple[Consulta, ...] = (
    Consulta(
        nome="gasto_por_categoria",
        pergunta="Em que a cota e gasta?",
        sql="""
            SELECT categoria,
                   count(*)                AS lancamentos,
                   round(sum(valor_liquido), 2) AS total
            FROM tabela
            GROUP BY categoria
            ORDER BY total DESC
        """,
    ),
    Consulta(
        nome="gasto_medio_por_uf",
        pergunta="Quanto gasta, em media, um deputado de cada estado?",
        sql="""
            SELECT uf,
                   count(DISTINCT ide_cadastro) AS deputados,
                   round(sum(valor_liquido), 2) AS total,
                   round(sum(valor_liquido) / count(DISTINCT ide_cadastro), 2) AS media_por_deputado
            FROM tabela
            WHERE uf <> ''
            GROUP BY uf
            ORDER BY media_por_deputado DESC
        """,
        ressalva=(
            "A media por UF reflete o valor da cota daquele estado, que e maior quanto mais "
            "longe de Brasilia. Nao le como eficiencia nem como zelo."
        ),
    ),
    Consulta(
        nome="fornecedores_mais_frequentes",
        pergunta="Quais fornecedores aparecem para mais deputados diferentes?",
        sql="""
            SELECT fornecedor,
                   documento_fornecedor,
                   count(DISTINCT ide_cadastro) AS deputados_atendidos,
                   count(*)                     AS lancamentos,
                   round(sum(valor_liquido), 2) AS total
            FROM tabela
            WHERE tipo_documento_fornecedor = 'cnpj'
            GROUP BY fornecedor, documento_fornecedor
            HAVING count(DISTINCT ide_cadastro) > 1
            ORDER BY deputados_atendidos DESC, total DESC
            LIMIT 25
        """,
        ressalva=(
            "Atender muitos gabinetes e esperado para companhia aerea, rede de hotel e "
            "operadora de telefonia. A lista e ponto de partida de leitura, nao achado."
        ),
    ),
    Consulta(
        nome="glosas_por_categoria",
        pergunta="Onde a Camara mais contesta valor apresentado?",
        sql="""
            SELECT categoria,
                   count(*) FILTER (WHERE valor_glosa > 0) AS lancamentos_glosados,
                   count(*)                                AS lancamentos,
                   round(sum(valor_glosa), 2)              AS total_glosado
            FROM tabela
            GROUP BY categoria
            HAVING sum(valor_glosa) > 0
            ORDER BY total_glosado DESC
        """,
        ressalva=(
            "Glosa e a Casa recusando parte do valor. Aparecer aqui indica que o controle "
            "funcionou naquele lancamento, nao que houve irregularidade."
        ),
    ),
    Consulta(
        nome="estornos",
        pergunta="Quanto foi devolvido?",
        sql="""
            SELECT count(*)                     AS lancamentos,
                   round(sum(valor_liquido), 2) AS total
            FROM tabela
            WHERE valor_liquido < 0
        """,
    ),
    Consulta(
        nome="concentracao_por_deputado",
        pergunta="Para cada deputado, que fatia do gasto foi para um unico fornecedor?",
        sql="""
            WITH por_fornecedor AS (
                SELECT ide_cadastro, parlamentar, uf, fornecedor,
                       sum(valor_liquido) AS gasto
                FROM tabela
                WHERE valor_liquido > 0
                GROUP BY ide_cadastro, parlamentar, uf, fornecedor
            ),
            total AS (
                SELECT ide_cadastro, sum(gasto) AS gasto_total
                FROM por_fornecedor GROUP BY ide_cadastro
            )
            SELECT p.parlamentar, p.uf, p.fornecedor,
                   round(p.gasto, 2)                        AS gasto_no_fornecedor,
                   round(t.gasto_total, 2)                  AS gasto_total,
                   round(100 * p.gasto / t.gasto_total, 1)  AS percentual
            FROM por_fornecedor p
            JOIN total t USING (ide_cadastro)
            WHERE t.gasto_total > 0
            QUALIFY row_number() OVER (PARTITION BY p.ide_cadastro ORDER BY p.gasto DESC) = 1
            ORDER BY percentual DESC
            LIMIT 25
        """,
        ressalva=(
            "Concentracao alta tem explicacao banal na maioria dos casos: gabinete que usa "
            "um unico contrato de aluguel, ou deputado com poucos lancamentos no ano."
        ),
    ),
)


def conectar(parquet: str | Path):
    """Abre o DuckDB com a tabela limpa registrada como `tabela`."""
    import duckdb

    conexao = duckdb.connect()
    conexao.execute(
        f"CREATE VIEW tabela AS SELECT * FROM read_parquet('{Path(parquet).as_posix()}')"
    )
    return conexao


def executar(conexao, consulta: Consulta) -> list[dict[str, Any]]:
    """Roda uma consulta e devolve linhas como dicionarios."""
    resultado = conexao.execute(consulta.sql)
    colunas = [d[0] for d in resultado.description]
    return [dict(zip(colunas, linha, strict=True)) for linha in resultado.fetchall()]


def executar_todas(parquet: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Roda todas as consultas declaradas e devolve os resultados por nome."""
    conexao = conectar(parquet)
    try:
        return {c.nome: executar(conexao, c) for c in CONSULTAS}
    finally:
        conexao.close()
