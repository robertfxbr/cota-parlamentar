import json

import pytest

from cota.cli import main
from cota.fonte import FonteError


@pytest.fixture
def sem_rede(monkeypatch, zip_de_teste):
    """O CLI baixaria o arquivo da Camara; aqui ele recebe o zip de teste."""
    monkeypatch.setattr("cota.cli.baixar", lambda ano, dados: zip_de_teste)


def test_preparar_imprime_o_resumo(sem_rede, tmp_path, capsys):
    assert main(["preparar", "2025", "--dados", str(tmp_path)]) == 0
    saida = capsys.readouterr().out
    resumo = json.loads(saida[: saida.index("tabela limpa")])
    assert resumo["lidas"] == 6
    assert resumo["descartadas_nao_parlamentar"] == 1
    assert "LIDERANCA DO PT" in resumo["nomes_nao_parlamentares"]


def test_relatorio_grava_o_markdown(sem_rede, tmp_path, capsys):
    destino = tmp_path / "saida" / "2025.md"
    assert main(["relatorio", "2025", "--dados", str(tmp_path), "--saida", str(destino)]) == 0
    texto = destino.read_text(encoding="utf-8")
    assert "# Cota parlamentar — 2025" in texto
    assert "O que entrou e o que caiu" in texto
    assert "4 lancamentos analisados" in capsys.readouterr().out.replace(".", "")


def test_relatorio_nao_publica_documento_de_pessoa_fisica(sem_rede, tmp_path):
    """A garantia atravessa o programa inteiro, ate o arquivo publicado."""
    destino = tmp_path / "2025.md"
    main(["relatorio", "2025", "--dados", str(tmp_path), "--saida", str(destino)])
    texto = destino.read_text(encoding="utf-8")
    assert "12345678900" not in texto
    assert "11122233344" not in texto


def test_consultas_lista_as_perguntas_e_o_sql(capsys):
    assert main(["consultas"]) == 0
    saida = capsys.readouterr().out
    assert "Em que a cota e gasta?" in saida
    assert "SELECT" in saida
    assert "como ler:" in saida


def test_ano_invalido_devolve_dois(monkeypatch, capsys):
    def recusa(ano, dados):
        raise FonteError("a Camara publica a cota a partir de 2009; pedido: 1990")

    monkeypatch.setattr("cota.cli.baixar", recusa)
    assert main(["preparar", "1990"]) == 2
    assert "2009" in capsys.readouterr().err


def test_sem_subcomando_o_argparse_recusa():
    with pytest.raises(SystemExit):
        main([])
