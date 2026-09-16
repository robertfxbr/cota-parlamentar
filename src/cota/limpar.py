"""Limpeza e classificacao de um lancamento da cota.

Todas as funcoes daqui sao puras e recebem o registro como dicionario de
texto, que e o formato cru do CSV. E onde mora a logica que decide o que entra
na analise - por isso e o que tem teste, e nao o notebook.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .esquema import COLUNAS_DESCARTADAS

Registro = dict[str, str]

_SO_DIGITO = re.compile(r"\D")


def normalizar_cabecalho(colunas: list[str]) -> list[str]:
    """Tira BOM e aspas dos nomes de coluna.

    O arquivo da Camara comeca com BOM e publica a primeira coluna entre
    aspas, entao sem isso `txNomeParlamentar` nunca casa e a coluna some da
    analise sem nenhum erro aparente.
    """
    return [c.replace("﻿", "").strip().strip('"') for c in colunas]


def texto(valor: str | None) -> str:
    """Colapsa espacos e devolve string vazia para ausente."""
    if not valor:
        return ""
    return re.sub(r"\s+", " ", valor).strip()


def sem_acento(valor: str) -> str:
    """Versao sem acento e em maiuscula, para comparar nome de fornecedor."""
    normalizado = unicodedata.normalize("NFKD", texto(valor))
    return normalizado.encode("ascii", "ignore").decode("ascii").upper()


def numero(valor: str | None) -> float:
    """Le os valores monetarios do arquivo, que usam ponto decimal.

    Devolve 0.0 para vazio: no arquivo, campo de valor em branco significa
    ausencia de valor, nao valor desconhecido.
    """
    limpo = texto(valor).replace(",", ".")
    if not limpo:
        return 0.0
    try:
        return float(limpo)
    except ValueError:
        return 0.0


def e_parlamentar(registro: Registro) -> bool:
    """Diz se o lancamento pertence a um deputado.

    Lideranca partidaria e Lideranca do Governo tambem usam a cota e aparecem
    na mesma coluna de nome. Sem este filtro, elas entram no ranking de
    deputados que mais gastam - e um ranking com "LIDERANCA DO PT" no meio nao
    responde a pergunta que alguem fez.
    """
    return bool(texto(registro.get("ideCadastro")))


@dataclass(frozen=True)
class Documento:
    """Um CNPJ ou CPF de fornecedor, ja classificado."""

    digitos: str
    tipo: str  # "cnpj" | "cpf" | "invalido"

    @property
    def e_pessoa_fisica(self) -> bool:
        return self.tipo == "cpf"


def classificar_documento(valor: str | None) -> Documento:
    """Classifica o documento do fornecedor pelo numero de digitos.

    A pontuacao no arquivo nao e confiavel - aparecem CNPJs escritos como
    "085.324.290/0013-1", que nao e mascara valida de CNPJ nem de CPF. Por isso
    a classificacao olha a quantidade de digitos e ignora a formatacao.
    """
    digitos = _SO_DIGITO.sub("", texto(valor))
    if len(digitos) == 14:
        return Documento(digitos, "cnpj")
    if len(digitos) == 11:
        return Documento(digitos, "cpf")
    return Documento(digitos, "invalido")


def mascarar_cpf(digitos: str) -> str:
    """Esconde o miolo de um CPF, preservando o suficiente para agrupar.

    Fornecedor pessoa fisica nao e agente publico. Da para contar quantas vezes
    o mesmo prestador aparece sem publicar o documento dele inteiro.
    """
    if len(digitos) != 11:
        return "***"
    return f"***{digitos[3:6]}***"


def anonimizar(registro: Registro) -> Registro:
    """Remove as colunas pessoais e mascara CPF de fornecedor.

    Aplicado na carga, antes de qualquer analise, para que nenhum caminho do
    programa consiga vazar o que foi descartado aqui.
    """
    limpo = {k: v for k, v in registro.items() if k not in COLUNAS_DESCARTADAS}
    documento = classificar_documento(registro.get("txtCNPJCPF"))
    if documento.e_pessoa_fisica:
        limpo["txtCNPJCPF"] = mascarar_cpf(documento.digitos)
        limpo["tipoDocumentoFornecedor"] = "cpf"
    else:
        limpo["txtCNPJCPF"] = documento.digitos
        limpo["tipoDocumentoFornecedor"] = documento.tipo
    return limpo


def valor_efetivo(registro: Registro) -> float:
    """O que de fato saiu do dinheiro publico naquele lancamento.

    E `vlrLiquido`, nao `vlrDocumento`: a diferenca entre os dois e a glosa, a
    parte contestada que nao foi paga. Somar `vlrDocumento` superestima o gasto
    em toda linha glosada - sao 9.879 linhas em 2025.
    """
    return numero(registro.get("vlrLiquido"))


def e_estorno(registro: Registro) -> bool:
    """Lancamento de devolucao, com valor negativo.

    Sao 8.017 linhas em 2025. Entram na soma normalmente, porque reduzem o
    total de verdade; a funcao existe para poder conta-las no relatorio.
    """
    return valor_efetivo(registro) < 0
