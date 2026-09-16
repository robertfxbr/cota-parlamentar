"""Geracao do relatorio em Markdown.

O relatorio e saida, nunca fonte: ele e regenerado pelo CI a cada push, entao
nao ha como o texto publicado divergir do codigo que o produziu. E a resposta
ao defeito classico do portfolio de dados - o notebook com resultado colado
que ninguem consegue reproduzir.
"""

from __future__ import annotations

from typing import Any

from .analise import CONSULTAS
from .preparar import Resumo


def milhar(valor: int) -> str:
    """Formata inteiro no padrao brasileiro, sem tocar em nenhum outro texto."""
    return f"{valor:,}".replace(",", ".")


def moeda(valor: Any) -> str:
    """Formata valor monetario no padrao brasileiro."""
    if not isinstance(valor, int | float):
        return str(valor)
    inteiro, _, centavos = f"{abs(valor):,.2f}".partition(".")
    return f"{'-' if valor < 0 else ''}R$ {inteiro.replace(',', '.')},{centavos}"


def _celula(coluna: str, valor: Any) -> str:
    if valor is None:
        return ""
    if coluna.startswith(("total", "gasto", "media", "valor")):
        return moeda(valor)
    if coluna == "percentual":
        return f"{valor}%"
    if isinstance(valor, int):
        return milhar(valor)
    return str(valor)


def tabela_markdown(linhas: list[dict[str, Any]], limite: int = 15) -> str:
    """Formata o resultado de uma consulta como tabela."""
    if not linhas:
        return "_Sem resultados._"

    colunas = list(linhas[0])
    cabecalho = "| " + " | ".join(colunas) + " |"
    separador = "|" + "|".join("---" for _ in colunas) + "|"
    corpo = [
        "| " + " | ".join(_celula(c, linha.get(c)) for c in colunas) + " |"
        for linha in linhas[:limite]
    ]
    saida = "\n".join([cabecalho, separador, *corpo])
    if len(linhas) > limite:
        saida += f"\n\n_{milhar(len(linhas) - limite)} linha(s) a mais foram omitidas._"
    return saida


def _tabela_do_resumo(resumo: Resumo) -> list[str]:
    linhas = [
        ("lidas do arquivo", resumo.lidas),
        ("mantidas na análise", resumo.mantidas),
        ("descartadas — não são de deputado", resumo.descartadas_nao_parlamentar),
        ("descartadas — valor líquido zero", resumo.descartadas_sem_valor),
        ("estornos — valor negativo", resumo.estornos),
        ("com glosa — valor contestado", resumo.linhas_com_glosa),
        ("fornecedor pessoa física — documento mascarado", resumo.fornecedores_pessoa_fisica),
    ]
    return ["| | linhas |", "|---|---|"] + [f"| {rotulo} | {milhar(n)} |" for rotulo, n in linhas]


def montar(
    ano: int,
    resultados: dict[str, list[dict[str, Any]]],
    resumo: Resumo,
    gerado_em: str,
) -> str:
    """Monta o relatorio inteiro, comecando pelo que foi descartado."""
    partes = [
        f"# Cota parlamentar — {ano}",
        "",
        f"Gerado automaticamente em {gerado_em} a partir do arquivo publicado pela Câmara "
        "dos Deputados. Este arquivo é saída do programa: não edite à mão.",
        "",
        "## O que entrou e o que caiu",
        "",
        "Vem primeiro de propósito. Um número de gasto só significa alguma coisa depois "
        "de se saber o que foi excluído para chegar nele.",
        "",
        *_tabela_do_resumo(resumo),
        "",
    ]

    if resumo.nomes_nao_parlamentares:
        nomes = ", ".join(f"`{n}`" for n in sorted(resumo.nomes_nao_parlamentares))
        partes += [
            "As entradas descartadas por não pertencerem a um deputado são estruturas da "
            f"Casa que também usam a cota: {nomes}.",
            "",
        ]

    for consulta in CONSULTAS:
        partes += [f"## {consulta.pergunta}", ""]
        if consulta.ressalva:
            partes += [f"> **Como ler:** {consulta.ressalva}", ""]
        partes += [tabela_markdown(resultados.get(consulta.nome, [])), ""]

    partes += [
        "---",
        "",
        "Fonte: Câmara dos Deputados, arquivo anual da Cota para Exercício da Atividade "
        "Parlamentar. O dado bruto não é versionado neste repositório; o programa o baixa "
        "da fonte oficial quando executado.",
        "",
    ]
    return "\n".join(partes)
