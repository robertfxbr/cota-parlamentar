import pytest

from cota.analise import CONSULTAS, executar_todas
from cota.preparar import Resumo, gravar_parquet
from cota.relatorio import milhar, moeda, montar, tabela_markdown

LINHAS = [
    {
        "parlamentar": "Deputado Um",
        "ide_cadastro": "1001",
        "uf": "PR",
        "partido": "A",
        "categoria": "COMBUSTIVEIS",
        "fornecedor": "POSTO X",
        "documento_fornecedor": "111",
        "tipo_documento_fornecedor": "cnpj",
        "tipo_documento": "0",
        "data_emissao": "2025-01-05",
        "valor_documento": 300.0,
        "valor_glosa": 0.0,
        "valor_liquido": 300.0,
        "mes": "1",
        "ano": "2025",
        "url_documento": "u1",
    },
    {
        "parlamentar": "Deputado Um",
        "ide_cadastro": "1001",
        "uf": "PR",
        "partido": "A",
        "categoria": "DIVULGACAO",
        "fornecedor": "GRAFICA Y",
        "documento_fornecedor": "222",
        "tipo_documento_fornecedor": "cnpj",
        "tipo_documento": "0",
        "data_emissao": "2025-02-05",
        "valor_documento": 1000.0,
        "valor_glosa": 250.0,
        "valor_liquido": 750.0,
        "mes": "2",
        "ano": "2025",
        "url_documento": "u2",
    },
    {
        "parlamentar": "Deputado Dois",
        "ide_cadastro": "1002",
        "uf": "AC",
        "partido": "B",
        "categoria": "COMBUSTIVEIS",
        "fornecedor": "POSTO X",
        "documento_fornecedor": "111",
        "tipo_documento_fornecedor": "cnpj",
        "tipo_documento": "0",
        "data_emissao": "2025-03-05",
        "valor_documento": 5000.0,
        "valor_glosa": 0.0,
        "valor_liquido": 5000.0,
        "mes": "3",
        "ano": "2025",
        "url_documento": "u3",
    },
    {
        "parlamentar": "Deputado Dois",
        "ide_cadastro": "1002",
        "uf": "AC",
        "partido": "B",
        "categoria": "COMBUSTIVEIS",
        "fornecedor": "POSTO X",
        "documento_fornecedor": "111",
        "tipo_documento_fornecedor": "cnpj",
        "tipo_documento": "0",
        "data_emissao": "2025-04-05",
        "valor_documento": -120.0,
        "valor_glosa": 0.0,
        "valor_liquido": -120.0,
        "mes": "4",
        "ano": "2025",
        "url_documento": "u4",
    },
]


@pytest.fixture
def parquet(tmp_path):
    return gravar_parquet(LINHAS, tmp_path / "cota.parquet")


@pytest.fixture
def resultados(parquet):
    return executar_todas(parquet)


def test_toda_consulta_declarada_roda(resultados):
    assert set(resultados) == {c.nome for c in CONSULTAS}


def test_gasto_por_categoria_soma_o_liquido(resultados):
    por_categoria = {x["categoria"]: x["total"] for x in resultados["gasto_por_categoria"]}
    assert por_categoria["COMBUSTIVEIS"] == pytest.approx(5180.0)  # 300 + 5000 - 120
    assert por_categoria["DIVULGACAO"] == pytest.approx(750.0)  # liquido, nao 1000


def test_media_por_uf_divide_por_deputados_distintos(resultados):
    por_uf = {linha["uf"]: linha for linha in resultados["gasto_medio_por_uf"]}
    assert por_uf["PR"]["deputados"] == 1
    assert por_uf["PR"]["media_por_deputado"] == pytest.approx(1050.0)


def test_fornecedor_que_atende_mais_de_um_deputado_aparece(resultados):
    fornecedores = {x["fornecedor"]: x for x in resultados["fornecedores_mais_frequentes"]}
    assert fornecedores["POSTO X"]["deputados_atendidos"] == 2
    assert "GRAFICA Y" not in fornecedores  # atende so um deputado


def test_glosa_aparece_na_categoria_certa(resultados):
    glosas = {x["categoria"]: x for x in resultados["glosas_por_categoria"]}
    assert glosas["DIVULGACAO"]["total_glosado"] == pytest.approx(250.0)
    assert "COMBUSTIVEIS" not in glosas


def test_estornos_sao_contados(resultados):
    assert resultados["estornos"][0]["lancamentos"] == 1
    assert resultados["estornos"][0]["total"] == pytest.approx(-120.0)


def test_concentracao_traz_um_fornecedor_por_deputado(resultados):
    linhas = resultados["concentracao_por_deputado"]
    assert len(linhas) == 2
    dois = next(x for x in linhas if x["parlamentar"] == "Deputado Dois")
    assert dois["percentual"] == pytest.approx(100.0)


def test_nenhuma_consulta_ordena_deputado_por_valor_bruto():
    """A comparacao entre estados mede distancia de Brasilia, nao comportamento."""
    for consulta in CONSULTAS:
        sql = " ".join(consulta.sql.split()).lower()
        if "order by" in sql and "parlamentar" in sql.split("order by")[1][:60]:
            raise AssertionError(f"{consulta.nome} ordena parlamentar por valor")


def test_consulta_com_ressalva_tem_texto():
    com_ressalva = [c for c in CONSULTAS if c.ressalva]
    assert len(com_ressalva) >= 3
    assert all(len(c.ressalva) > 40 for c in com_ressalva)


def test_moeda_formata_no_padrao_brasileiro():
    assert moeda(1234567.8) == "R$ 1.234.567,80"
    assert moeda(-120.5) == "-R$ 120,50"


def test_milhar_nao_toca_em_texto():
    assert milhar(209066) == "209.066"


def test_tabela_markdown_vazia():
    assert tabela_markdown([]) == "_Sem resultados._"


def test_tabela_markdown_limita_e_avisa():
    linhas = [{"a": i} for i in range(20)]
    saida = tabela_markdown(linhas, limite=5)
    assert "15 linha(s) a mais" in saida


def test_relatorio_comeca_pelo_que_foi_descartado(resultados):
    resumo = Resumo(lidas=100, mantidas=90, descartadas_nao_parlamentar=10)
    texto = montar(2025, resultados, resumo, "01/01/2026 00:00 UTC")
    posicao_descarte = texto.index("O que entrou e o que caiu")
    posicao_primeira_pergunta = texto.index(CONSULTAS[0].pergunta)
    assert posicao_descarte < posicao_primeira_pergunta


def test_relatorio_nomeia_as_entradas_descartadas(resultados):
    resumo = Resumo(nomes_nao_parlamentares={"LIDERANCA DO PT"})
    assert "LIDERANCA DO PT" in montar(2025, resultados, resumo, "x")


def test_relatorio_traz_as_ressalvas(resultados):
    texto = montar(2025, resultados, Resumo(), "x")
    assert "Como ler:" in texto
    assert "distância de Brasília" in texto or "Brasilia" in texto


def test_relatorio_avisa_que_e_saida_do_programa(resultados):
    assert "não edite à mão" in montar(2025, resultados, Resumo(), "x")


def test_moeda_devolve_texto_intacto_quando_nao_e_numero():
    assert moeda(None) == "None"
    assert moeda("ate agora") == "ate agora"


def test_celula_vazia_para_ausente():
    from cota.relatorio import _celula

    assert _celula("total", None) == ""
    assert _celula("uf", "PR") == "PR"
