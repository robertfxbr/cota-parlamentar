"""Transformacao do arquivo cru em uma tabela limpa.

Este e o unico ponto do programa em que o dado cru vira dado analisavel, e por
isso e o ponto em que as decisoes ficam registradas: o que foi descartado,
quantas linhas cairam e por que. O relatorio publica essa contagem - uma
limpeza que ninguem consegue auditar e indistinguivel de uma limpeza errada.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .limpar import (
    Registro,
    anonimizar,
    e_estorno,
    e_parlamentar,
    numero,
    texto,
    valor_efetivo,
)

CAMPOS_DA_TABELA = (
    "parlamentar",
    "ide_cadastro",
    "uf",
    "partido",
    "categoria",
    "fornecedor",
    "documento_fornecedor",
    "tipo_documento_fornecedor",
    "tipo_documento",
    "data_emissao",
    "valor_documento",
    "valor_glosa",
    "valor_liquido",
    "mes",
    "ano",
    "url_documento",
)


@dataclass
class Resumo:
    """O que aconteceu na limpeza."""

    lidas: int = 0
    mantidas: int = 0
    descartadas_nao_parlamentar: int = 0
    descartadas_sem_valor: int = 0
    estornos: int = 0
    linhas_com_glosa: int = 0
    fornecedores_pessoa_fisica: int = 0
    nomes_nao_parlamentares: set[str] = field(default_factory=set)

    def como_dicionario(self) -> dict[str, object]:
        return {
            "lidas": self.lidas,
            "mantidas": self.mantidas,
            "descartadas_nao_parlamentar": self.descartadas_nao_parlamentar,
            "descartadas_sem_valor": self.descartadas_sem_valor,
            "estornos": self.estornos,
            "linhas_com_glosa": self.linhas_com_glosa,
            "fornecedores_pessoa_fisica": self.fornecedores_pessoa_fisica,
            "nomes_nao_parlamentares": sorted(self.nomes_nao_parlamentares),
        }


def _linha(registro: Registro) -> dict[str, object]:
    return {
        "parlamentar": texto(registro.get("txNomeParlamentar")),
        "ide_cadastro": texto(registro.get("ideCadastro")),
        "uf": texto(registro.get("sgUF")),
        "partido": texto(registro.get("sgPartido")),
        "categoria": texto(registro.get("txtDescricao")),
        "fornecedor": texto(registro.get("txtFornecedor")),
        "documento_fornecedor": texto(registro.get("txtCNPJCPF")),
        "tipo_documento_fornecedor": texto(registro.get("tipoDocumentoFornecedor")),
        "tipo_documento": texto(registro.get("indTipoDocumento")),
        "data_emissao": texto(registro.get("datEmissao"))[:10],
        "valor_documento": numero(registro.get("vlrDocumento")),
        "valor_glosa": numero(registro.get("vlrGlosa")),
        "valor_liquido": valor_efetivo(registro),
        "mes": texto(registro.get("numMes")),
        "ano": texto(registro.get("numAno")),
        "url_documento": texto(registro.get("urlDocumento")),
    }


def preparar(registros: Iterable[Registro]) -> tuple[list[dict[str, object]], Resumo]:
    """Limpa, anonimiza e filtra, devolvendo a tabela e o resumo do que caiu."""
    resumo = Resumo()
    tabela: list[dict[str, object]] = []

    for cru in registros:
        resumo.lidas += 1

        if not e_parlamentar(cru):
            resumo.descartadas_nao_parlamentar += 1
            resumo.nomes_nao_parlamentares.add(texto(cru.get("txNomeParlamentar")))
            continue

        limpo = anonimizar(cru)
        if valor_efetivo(limpo) == 0:
            resumo.descartadas_sem_valor += 1
            continue

        if e_estorno(limpo):
            resumo.estornos += 1
        if numero(limpo.get("vlrGlosa")) > 0:
            resumo.linhas_com_glosa += 1
        if limpo.get("tipoDocumentoFornecedor") == "cpf":
            resumo.fornecedores_pessoa_fisica += 1

        tabela.append(_linha(limpo))
        resumo.mantidas += 1

    return tabela, resumo


def gravar_parquet(tabela: list[dict[str, object]], destino: str | Path) -> Path:
    """Grava a tabela limpa em Parquet, formato que o DuckDB consulta direto."""
    try:
        import polars as pl
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise RuntimeError("polars nao instalado. Use: pip install -e '.[dev]'") from exc

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        tabela, schema={c: (pl.Float64 if "valor" in c else pl.Utf8) for c in CAMPOS_DA_TABELA}
    ).write_parquet(destino)
    return destino
