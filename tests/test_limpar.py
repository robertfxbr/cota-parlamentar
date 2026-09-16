import pytest

from cota.limpar import (
    anonimizar,
    classificar_documento,
    e_estorno,
    e_parlamentar,
    mascarar_cpf,
    normalizar_cabecalho,
    numero,
    sem_acento,
    texto,
    valor_efetivo,
)


def test_normalizar_cabecalho_tira_bom_e_aspas():
    """Sem isso a primeira coluna nunca casa e some da analise, sem erro."""
    bruto = ['﻿"txNomeParlamentar"', "cpf", " sgUF "]
    assert normalizar_cabecalho(bruto) == ["txNomeParlamentar", "cpf", "sgUF"]


@pytest.mark.parametrize(
    "bruto, esperado", [("  a  b ", "a b"), ("a\nb", "a b"), (None, ""), ("", "")]
)
def test_texto(bruto, esperado):
    assert texto(bruto) == esperado


def test_sem_acento_para_comparar_fornecedor():
    assert sem_acento("Padaria Açúcar & Cia") == "PADARIA ACUCAR & CIA"


@pytest.mark.parametrize(
    "bruto, esperado",
    [
        ("1467", 1467.0),
        ("1467.50", 1467.5),
        ("1467,50", 1467.5),
        ("-30", -30.0),
        ("", 0.0),
        ("abc", 0.0),
        (None, 0.0),
    ],
)
def test_numero(bruto, esperado):
    assert numero(bruto) == esperado


def test_e_parlamentar_aceita_deputado():
    assert e_parlamentar({"txNomeParlamentar": "Fulano", "ideCadastro": "204379"})


@pytest.mark.parametrize("valor", ["", "   ", None])
def test_lideranca_nao_e_parlamentar(valor):
    """As 12 liderancas do arquivo de 2025 nao tem ideCadastro."""
    assert not e_parlamentar({"txNomeParlamentar": "LIDERANCA DO PT", "ideCadastro": valor})


@pytest.mark.parametrize(
    "bruto, tipo",
    [
        ("12.345.678/0001-95", "cnpj"),
        ("085.324.290/0013-1", "cnpj"),  # mascara invalida no arquivo, 14 digitos
        ("123.456.789-00", "cpf"),
        ("12345678900", "cpf"),
        ("123", "invalido"),
        ("", "invalido"),
        (None, "invalido"),
    ],
)
def test_classificar_documento_ignora_a_pontuacao(bruto, tipo):
    assert classificar_documento(bruto).tipo == tipo


def test_classificar_documento_guarda_so_digitos():
    assert classificar_documento("12.345.678/0001-95").digitos == "12345678000195"


def test_mascarar_cpf_preserva_o_suficiente_para_agrupar():
    assert mascarar_cpf("12345678900") == "***456***"


def test_mascarar_cpf_recusa_tamanho_errado():
    assert mascarar_cpf("123") == "***"


def test_anonimizar_remove_o_cpf_do_parlamentar():
    """A coluna vem preenchida no arquivo publico e nao serve a nenhuma pergunta aqui."""
    cru = {"txNomeParlamentar": "Fulano", "cpf": "12345678900", "txtCNPJCPF": "12.345.678/0001-95"}
    limpo = anonimizar(cru)
    assert "cpf" not in limpo
    assert "12345678900" not in str(limpo)


def test_anonimizar_remove_nome_de_passageiro():
    cru = {"txtPassageiro": "Terceiro Qualquer", "txtCNPJCPF": ""}
    assert "txtPassageiro" not in anonimizar(cru)


def test_anonimizar_mascara_fornecedor_pessoa_fisica():
    limpo = anonimizar({"txtCNPJCPF": "123.456.789-00"})
    assert limpo["txtCNPJCPF"] == "***456***"
    assert limpo["tipoDocumentoFornecedor"] == "cpf"


def test_anonimizar_preserva_cnpj_inteiro():
    """Empresa fornecedora do poder publico nao tem a mesma protecao de pessoa fisica."""
    limpo = anonimizar({"txtCNPJCPF": "12.345.678/0001-95"})
    assert limpo["txtCNPJCPF"] == "12345678000195"
    assert limpo["tipoDocumentoFornecedor"] == "cnpj"


def test_valor_efetivo_usa_o_liquido_e_nao_o_do_documento():
    """A diferenca e a glosa: somar vlrDocumento superestima toda linha glosada."""
    registro = {"vlrDocumento": "1000", "vlrGlosa": "250", "vlrLiquido": "750"}
    assert valor_efetivo(registro) == 750.0


def test_estorno_e_valor_negativo():
    assert e_estorno({"vlrLiquido": "-120.50"})
    assert not e_estorno({"vlrLiquido": "120.50"})
