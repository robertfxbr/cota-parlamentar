"""O esquema publicado pela Camara, e o que ele nao diz.

Tudo aqui foi conferido contra o arquivo de 2025, nao copiado da
documentacao. O motivo e concreto: o endpoint por deputado da API
(`/deputados/{id}/despesas`) devolve HTTP 200 com lista vazia para todos os
parlamentares testados, em todos os anos. Uma documentacao cujo endpoint
principal nao entrega dado nao serve de referencia confiavel, entao as
constantes abaixo saem da observacao do arquivo.
"""

from __future__ import annotations

# As 32 colunas do arquivo. A primeira chega com BOM e entre aspas no cabecalho.
COLUNAS = (
    "txNomeParlamentar",
    "cpf",
    "ideCadastro",
    "nuCarteiraParlamentar",
    "nuLegislatura",
    "sgUF",
    "sgPartido",
    "codLegislatura",
    "numSubCota",
    "txtDescricao",
    "numEspecificacaoSubCota",
    "txtDescricaoEspecificacao",
    "txtFornecedor",
    "txtCNPJCPF",
    "txtNumero",
    "indTipoDocumento",
    "datEmissao",
    "vlrDocumento",
    "vlrGlosa",
    "vlrLiquido",
    "numMes",
    "numAno",
    "numParcela",
    "txtPassageiro",
    "txtTrecho",
    "numLote",
    "numRessarcimento",
    "datPagamentoRestituicao",
    "vlrRestituicao",
    "nuDeputadoId",
    "ideDocumento",
    "urlDocumento",
)

# Descartadas na carga por trazerem dado pessoal que a analise nao usa.
#
# `cpf` e o CPF do parlamentar e vem preenchido no arquivo publico. Republicar
# nao acrescenta nada a nenhuma pergunta deste projeto, e espalha dado pessoal
# por conta propria. `txtPassageiro` nomeia terceiros que viajaram, que nao sao
# agentes publicos e nunca escolheram aparecer.
COLUNAS_DESCARTADAS = ("cpf", "nuCarteiraParlamentar", "txtPassageiro")

# Codigos de `indTipoDocumento` observados no arquivo de 2025, com a contagem e
# um exemplo real de cada um.
#
# Nao ha rotulo aqui de proposito. A leitura corrente e que 0 seja nota fiscal
# e 2 despesa no exterior, mas no arquivo o tipo 2 aparece em "PASSAGEM AEREA -
# REEMBOLSO" e o tipo 3 em hospedagem no Uruguai. Como nao foi possivel
# confirmar o significado de cada codigo numa fonte que bata com o dado, este
# projeto preserva o codigo cru e nao inventa a traducao. Ver a secao "O que
# este dado nao permite concluir" no README.
TIPOS_DE_DOCUMENTO_OBSERVADOS = {
    0: {"linhas_2025": 109_992, "exemplo": "manutencao de escritorio, fornecedor nacional"},
    1: {"linhas_2025": 33_257, "exemplo": "locacao de veiculos, fornecedor nacional"},
    2: {"linhas_2025": 54, "exemplo": "passagem aerea - reembolso"},
    3: {"linhas_2025": 118, "exemplo": "hospedagem no exterior"},
    4: {"linhas_2025": 65_645, "exemplo": "sem amostra distinta dos demais"},
}

# Lancamentos que nao pertencem a um deputado: sao estruturas da Casa que
# tambem usam a cota. Sao 12 nomes e 937 linhas em 2025, todos comecando por
# "LID." ou "LIDERANCA DO".
#
# A deteccao usa `ideCadastro` vazio, e nao o texto do nome, porque os tres
# marcadores concordam exatamente nas mesmas 12 entradas (sem `sgUF`, sem
# `cpf`, sem `ideCadastro`) e um campo de identificador ausente e criterio mais
# estavel do que casar prefixo de string.
MARCADOR_DE_NAO_PARLAMENTAR = "ideCadastro"
