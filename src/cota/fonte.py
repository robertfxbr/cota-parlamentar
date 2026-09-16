"""Download do arquivo anual da cota, com cache em disco.

O dado nunca e versionado. Um arquivo de 6,6 MB por ano commitado no
repositorio deixaria o clone lento e envelheceria em silencio - o codigo baixa
quando precisa, e quem clona reproduz o resultado a partir da fonte oficial.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path

from .limpar import Registro, normalizar_cabecalho

URL_POR_ANO = "https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip"
PRIMEIRO_ANO = 2009


class FonteError(Exception):
    """Nao foi possivel obter o arquivo do ano pedido."""


def url_do_ano(ano: int) -> str:
    if ano < PRIMEIRO_ANO:
        raise FonteError(f"a Camara publica a cota a partir de {PRIMEIRO_ANO}; pedido: {ano}")
    return URL_POR_ANO.format(ano=ano)


def baixar(ano: int, diretorio: str | Path = "dados", baixador: Callable | None = None) -> Path:
    """Garante o arquivo do ano em disco e devolve o caminho.

    `baixador` e injetavel para que o teste nao dependa de rede.
    """
    destino = Path(diretorio) / f"Ano-{ano}.csv.zip"
    if destino.exists():
        return destino

    destino.parent.mkdir(parents=True, exist_ok=True)
    conteudo = (baixador or _baixar_http)(url_do_ano(ano))
    destino.write_bytes(conteudo)
    return destino


# (conexao, leitura). O timeout do requests e por leitura, nao total: um
# servidor que entrega os bytes devagar reseta o contador a cada pedaco e o
# download fica pendurado para sempre. Por isso ha tambem LIMITE_TOTAL.
TIMEOUT = (10, 30)
LIMITE_TOTAL = 120.0


def _baixar_http(url: str) -> bytes:  # pragma: no cover - exige rede
    """Baixa o arquivo, com teto de tempo total e erro tipado.

    Qualquer falha de rede vira FonteError: sem isso, uma queda de conexao sobe
    como traceback cru e o programa sai sem dizer o que aconteceu.
    """
    import time

    try:
        import requests
    except ImportError as exc:
        raise FonteError("requests nao instalado. Use: pip install -e '.[rede]'") from exc

    inicio = time.monotonic()
    try:
        resposta = requests.get(
            url,
            headers={"User-Agent": "cota-parlamentar/0.1 (+https://github.com/robertfxbr)"},
            timeout=TIMEOUT,
            stream=True,
        )
        if resposta.status_code != 200:
            raise FonteError(f"{url} devolveu {resposta.status_code}")

        pedacos = []
        for pedaco in resposta.iter_content(chunk_size=65_536):
            pedacos.append(pedaco)
            if time.monotonic() - inicio > LIMITE_TOTAL:
                raise FonteError(
                    f"{url} passou de {LIMITE_TOTAL:g}s de download; servidor lento ou instavel"
                )
        return b"".join(pedacos)
    except FonteError:
        raise
    except Exception as exc:
        raise FonteError(f"falha de rede ao buscar {url}: {type(exc).__name__}: {exc}") from exc


def ler_registros(caminho: str | Path) -> Iterator[Registro]:
    """Percorre o CSV de dentro do zip, uma linha por vez.

    Streaming, e nao carga inteira em memoria: sao mais de 200 mil linhas por
    ano, e a analise costuma pedir varios anos.
    """
    caminho = Path(caminho)
    try:
        with zipfile.ZipFile(caminho) as arquivo:
            interno = arquivo.namelist()[0]
            with arquivo.open(interno) as bruto:
                texto = io.TextIOWrapper(bruto, encoding="utf-8", errors="replace")
                leitor = csv.reader(texto, delimiter=";")
                cabecalho = normalizar_cabecalho(next(leitor))
                for linha in leitor:
                    # strict=False de proposito: uma linha com contagem de campos
                    # diferente nao pode derrubar a leitura das outras 200 mil. Ela
                    # chega com campos faltando, e a preparacao a descarta e conta.
                    yield dict(zip(cabecalho, linha, strict=False))
    except zipfile.BadZipFile as exc:
        raise FonteError(f"{caminho} nao e um zip valido: {exc}") from exc
