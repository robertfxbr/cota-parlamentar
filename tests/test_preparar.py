import pytest

from cota.fonte import FonteError, baixar, ler_registros, url_do_ano
from cota.preparar import gravar_parquet, preparar


def test_ler_registros_resolve_bom_e_aspas(zip_de_teste):
    primeiro = next(ler_registros(zip_de_teste))
    assert primeiro["txNomeParlamentar"] == "Deputado Um"


def test_preparar_conta_o_que_entrou_e_o_que_caiu(zip_de_teste):
    _, resumo = preparar(ler_registros(zip_de_teste))
    assert resumo.lidas == 6
    assert resumo.descartadas_nao_parlamentar == 1
    assert resumo.descartadas_sem_valor == 1
    assert resumo.mantidas == 4


def test_lideranca_fica_de_fora_e_e_nomeada(zip_de_teste):
    tabela, resumo = preparar(ler_registros(zip_de_teste))
    assert "LIDERANCA DO PT" in resumo.nomes_nao_parlamentares
    assert all("LIDERANCA" not in linha["parlamentar"] for linha in tabela)


def test_estorno_entra_na_tabela_e_e_contado(zip_de_teste):
    tabela, resumo = preparar(ler_registros(zip_de_teste))
    assert resumo.estornos == 1
    assert any(linha["valor_liquido"] == -120.50 for linha in tabela)


def test_glosa_e_contada_e_o_valor_usado_e_o_liquido(zip_de_teste):
    tabela, resumo = preparar(ler_registros(zip_de_teste))
    assert resumo.linhas_com_glosa == 1
    glosada = next(linha for linha in tabela if linha["valor_glosa"] == 250)
    assert glosada["valor_liquido"] == 750


def test_nenhum_cpf_de_parlamentar_sobrevive_a_preparacao(zip_de_teste):
    """A garantia central: o dado pessoal nao passa da carga."""
    tabela, _ = preparar(ler_registros(zip_de_teste))
    assert "11122233344" not in str(tabela)
    assert all("cpf" not in linha for linha in tabela)


def test_fornecedor_pessoa_fisica_sai_mascarado(zip_de_teste):
    tabela, resumo = preparar(ler_registros(zip_de_teste))
    assert resumo.fornecedores_pessoa_fisica == 1
    assert "12345678900" not in str(tabela)
    assert any(linha["documento_fornecedor"] == "***456***" for linha in tabela)


def test_gravar_parquet_produz_arquivo_legivel(zip_de_teste, tmp_path):
    import polars as pl

    tabela, _ = preparar(ler_registros(zip_de_teste))
    destino = gravar_parquet(tabela, tmp_path / "saida" / "cota.parquet")
    assert destino.exists()
    assert len(pl.read_parquet(destino)) == len(tabela)


def test_url_do_ano():
    assert url_do_ano(2025).endswith("Ano-2025.csv.zip")


def test_ano_anterior_ao_publicado_e_recusado():
    with pytest.raises(FonteError, match="2009"):
        url_do_ano(2001)


def test_baixar_usa_o_cache_e_nao_rebaixa(tmp_path, zip_de_teste):
    chamadas = []

    def falso(url):
        chamadas.append(url)
        return zip_de_teste.read_bytes()

    # diretorio proprio: a fixture ja gravou um Ano-2025.csv.zip em tmp_path
    destino = tmp_path / "cache"
    primeiro = baixar(2025, destino, baixador=falso)
    segundo = baixar(2025, destino, baixador=falso)
    assert primeiro == segundo
    assert len(chamadas) == 1


def test_zip_invalido_vira_erro_de_fonte(tmp_path):
    ruim = tmp_path / "ruim.zip"
    ruim.write_text("nao sou um zip", encoding="utf-8")
    with pytest.raises(FonteError, match="nao e um zip"):
        list(ler_registros(ruim))
