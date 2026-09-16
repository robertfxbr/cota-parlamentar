"""Interface de linha de comando."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .analise import CONSULTAS, executar_todas
from .fonte import FonteError, baixar, ler_registros
from .preparar import gravar_parquet, preparar
from .relatorio import montar


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cota",
        description="Analise reprodutivel da cota parlamentar da Camara dos Deputados.",
    )
    parser.add_argument("--version", action="version", version=f"cota {__version__}")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_prep = sub.add_parser("preparar", help="baixa o ano e grava a tabela limpa")
    p_prep.add_argument("ano", type=int)
    p_prep.add_argument("--dados", default="dados")

    p_rel = sub.add_parser("relatorio", help="gera o relatorio em Markdown")
    p_rel.add_argument("ano", type=int)
    p_rel.add_argument("--dados", default="dados")
    p_rel.add_argument("--saida", default=None)

    sub.add_parser("consultas", help="lista as perguntas e o SQL de cada uma")

    return parser


def _preparar_ano(ano: int, dados: str):
    caminho = baixar(ano, dados)
    tabela, resumo = preparar(ler_registros(caminho))
    parquet = gravar_parquet(tabela, Path(dados) / f"cota-{ano}.parquet")
    return parquet, resumo


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.comando == "consultas":
        for consulta in CONSULTAS:
            print(f"\n## {consulta.pergunta}  [{consulta.nome}]")
            if consulta.ressalva:
                print(f"   como ler: {consulta.ressalva}")
            print("   " + " ".join(consulta.sql.split()))
        return 0

    try:
        parquet, resumo = _preparar_ano(args.ano, args.dados)
    except FonteError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2

    if args.comando == "preparar":
        print(json.dumps(resumo.como_dicionario(), ensure_ascii=False, indent=2))
        print(f"tabela limpa em {parquet}")
        return 0

    resultados = executar_todas(parquet)
    texto = montar(
        args.ano,
        resultados,
        resumo,
        datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC"),
    )
    destino = Path(args.saida) if args.saida else Path("relatorio") / f"{args.ano}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8")
    print(f"{resumo.mantidas:,} lancamentos analisados -> {destino}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
