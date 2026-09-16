"""Fixtures compartilhadas.

O arquivo de teste e montado aqui, linha a linha, e nao recortado do arquivo
real da Camara: um recorte do arquivo real traria nome de deputado, CNPJ de
fornecedor e CPF para dentro do repositorio, que e exatamente o que o projeto
se propoe a nao publicar.

Cada linha existe por um motivo, e o motivo esta no comentario ao lado.
"""

import csv
import io
import zipfile

import pytest

CABECALHO = [
    '﻿"txNomeParlamentar"',  # o arquivo real vem com BOM e aspas
    "cpf",
    "ideCadastro",
    "sgUF",
    "sgPartido",
    "txtDescricao",
    "txtFornecedor",
    "txtCNPJCPF",
    "indTipoDocumento",
    "datEmissao",
    "vlrDocumento",
    "vlrGlosa",
    "vlrLiquido",
    "numMes",
    "numAno",
    "txtPassageiro",
    "urlDocumento",
]

CHAVES = [c.replace("﻿", "").strip('"') for c in CABECALHO]


def linha(**campos):
    """Um lancamento comum, com os campos que o teste quiser trocar."""
    padrao = {
        "txNomeParlamentar": "Deputado Um",
        "cpf": "11122233344",
        "ideCadastro": "1001",
        "sgUF": "PR",
        "sgPartido": "PARTIDO",
        "txtDescricao": "MANUTENCAO DE ESCRITORIO",
        "txtFornecedor": "EMPRESA LTDA",
        "txtCNPJCPF": "12.345.678/0001-95",
        "indTipoDocumento": "0",
        "datEmissao": "2025-02-07T00:00:00",
        "vlrDocumento": "1000",
        "vlrGlosa": "0",
        "vlrLiquido": "1000",
        "numMes": "2",
        "numAno": "2025",
        "txtPassageiro": "",
        "urlDocumento": "https://exemplo.test/doc/1",
    }
    padrao.update(campos)
    return padrao


LINHAS = (
    linha(),  # lancamento normal
    linha(txNomeParlamentar="LIDERANCA DO PT", cpf="", ideCadastro="", sgUF="NA"),  # nao e deputado
    linha(ideCadastro="1002", vlrLiquido="-120.50"),  # estorno
    linha(ideCadastro="1003", vlrLiquido="0"),  # sem valor, sai da analise
    linha(ideCadastro="1004", txtCNPJCPF="123.456.789-00", vlrLiquido="300"),  # fornecedor PF
    linha(ideCadastro="1005", vlrDocumento="1000", vlrGlosa="250", vlrLiquido="750"),  # glosado
)


@pytest.fixture
def zip_de_teste(tmp_path):
    """Um zip com o mesmo formato do publicado pela Camara."""
    destino = tmp_path / "Ano-2025.csv.zip"
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";", lineterminator="\n")
    escritor.writerow(CABECALHO)
    for registro in LINHAS:
        escritor.writerow([registro[c] for c in CHAVES])
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Ano-2025.csv", buffer.getvalue())
    return destino
