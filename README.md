# cota-parlamentar

Análise reprodutível da Cota para Exercício da Atividade Parlamentar da Câmara
dos Deputados — a verba que cada deputado usa para passagem, combustível,
aluguel de escritório e divulgação, com nota fiscal anexada a cada lançamento.

São **209.066 lançamentos em 2025**. O programa baixa o arquivo da fonte oficial,
limpa, anonimiza, responde seis perguntas em SQL e gera o relatório.

**A seção mais importante deste repositório é [o que este dado não permite
concluir](#o-que-este-dado-não-permite-concluir).** Ela vem antes dos resultados
de propósito.

[![CI](https://github.com/robertfxbr/cota-parlamentar/actions/workflows/ci.yml/badge.svg)](https://github.com/robertfxbr/cota-parlamentar/actions/workflows/ci.yml)

**[→ Relatório de 2025](relatorio/2025.md)**

## Uso

```bash
git clone git@github.com:robertfxbr/cota-parlamentar.git
cd cota-parlamentar
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[rede,dev]"

cota preparar 2025     # baixa, limpa e grava a tabela em Parquet
cota relatorio 2025    # gera relatorio/2025.md
cota consultas         # mostra as perguntas e o SQL de cada uma
```

## O que este dado não permite concluir

Esta seção existe porque a análise mais comum desse conjunto de dados — ordenar
deputados por valor gasto — está errada, e erra de um jeito que parece certo.

**Não dá para comparar o gasto de deputados de estados diferentes.** O valor da
cota varia por unidade federativa, porque embute o custo da passagem aérea entre
Brasília e o estado. Um deputado do Acre tem cota maior que um de São Paulo por
motivo geográfico, não por mérito. Ordenar os 513 por valor bruto produz um
ranking de distância até Brasília. **Por isso nenhuma consulta deste repositório
ordena parlamentar por valor**, e existe um teste que falha se alguém
acrescentar uma que o faça.

**Gastar toda a cota não é irregularidade, e gastar pouco não é virtude.** A cota
é um teto de reembolso de despesa comprovada. Quem gasta pouco pode ter
estrutura menor, mandato em fim de exercício, ou financiamento de outra origem.

**Glosa não é indício de fraude — é o indício oposto.** Glosa é a Câmara
recusando parte do valor apresentado. Uma linha glosada mostra o controle
interno tendo funcionado ali. São 9.852 linhas em 2025.

**Fornecedor que atende muitos gabinetes quase sempre tem explicação banal:**
companhia aérea, rede de hotel, operadora de telefonia. A consulta de
concentração é ponto de partida de leitura, não achado.

**O significado dos códigos de tipo de documento não foi confirmado.** A leitura
corrente é que `0` seja nota fiscal e `2` despesa no exterior, mas no arquivo
o tipo `2` aparece em "PASSAGEM AÉREA - REEMBOLSO" e o tipo `3` em hospedagem no
Uruguai. Como não foi possível casar nenhuma documentação com o dado, o código
cru é preservado e **nenhuma tradução é inventada**.

**Prior art:** a [Operação Serenata de Amor](https://serenata.ai/) trabalha esse
mesmo conjunto de dados desde 2016, com um classificador que sinaliza suspeitas.
Este projeto não tenta o que ela faz. Aqui não há suspeita levantada, nem
pontuação de deputado: é uma base limpa, auditável e reproduzível, com as
ressalvas escritas ao lado de cada número.

## As cinco decisões de projeto

**O que foi descartado é publicado antes do que foi encontrado.** O relatório
abre com a contagem: quantas linhas entraram, quantas caíram e por quê. Uma
limpeza que ninguém consegue auditar é indistinguível de uma limpeza errada.

**Lançamento que não é de deputado sai da base, e é nomeado.** Liderança do
Governo e as 11 lideranças partidárias também usam a cota e aparecem na mesma
coluna de nome — são 937 linhas em 2025. Quem agrupa por nome sem filtrar coloca
`LIDERANÇA DO PT` no meio do ranking de deputados. A detecção usa `ideCadastro`
vazio, e não o texto do nome, porque os três marcadores possíveis (sem `sgUF`,
sem `cpf`, sem `ideCadastro`) concordam exatamente nas mesmas 12 entradas.

**Dado pessoal não atravessa a carga.** O arquivo público traz o **CPF do
parlamentar** e o nome de passageiros que não são agentes públicos. Nenhum dos
dois responde a qualquer pergunta deste projeto, então são descartados na
entrada. Fornecedor pessoa física tem o documento mascarado, preservando só o
suficiente para agrupar. CNPJ de empresa fornecedora do poder público fica
inteiro. Há teste garantindo que nada disso sobrevive até o relatório.

**O valor somado é o líquido, não o do documento.** A diferença entre os dois é
a glosa. Somar `vlrDocumento` superestima o gasto em toda linha glosada.

**O relatório é saída, nunca fonte.** Um fluxo mensal do GitHub Actions
regenera `relatorio/` a partir do arquivo oficial e commita se mudou — e também
roda sob demanda, pelo botão. Ninguém edita aquele arquivo à mão, então o texto
publicado não tem como divergir do código que o produziu. É a resposta ao defeito
clássico do portfólio de dados: o notebook com resultado colado que ninguém
consegue reproduzir.

## Decisões rejeitadas

**A API da própria Câmara.** Seria a fonte natural, e não funciona:
`/deputados/{id}/despesas` devolve **HTTP 200 com lista vazia** para todos os
deputados testados, em todos os anos entre 2022 e 2026. O projeto usa o arquivo
anual em `camara.leg.br/cotas`, que entrega o dado completo. Consequência: as
constantes em `esquema.py` foram conferidas contra o arquivo, não copiadas de uma
documentação cujo endpoint principal não entrega nada.

**Versionar o CSV.** É o que a maioria dos portfólios de dados faz, e deixa
dezenas de megabytes no repositório que envelhecem em silêncio. Aqui o dado é
baixado da fonte oficial quando o programa roda, com cache local, e `dados/`
está no `.gitignore`.

**Jupyter.** Um notebook de meio megabyte carrega a saída embutida, o diff fica
ilegível e o histórico não conta nada. A lógica mora em `src/`, com teste; as
consultas moram em `analise.py`, em SQL legível; o relatório é Markdown gerado.

**pandas.** Polars e DuckDB não estão aqui por moda: são 209 mil linhas por ano,
e a pergunta de concentração por deputado é uma window function que em SQL cabe
em seis linhas.

**Regenerar o relatório dentro do CI de testes.** Era o desenho da primeira
versão, e ele quebrou na primeira execução: o job ficou pendurado baixando o
arquivo da Câmara a partir de um runner nos Estados Unidos. Dois defeitos
apareceram de uma vez. O `timeout` do `requests` é por leitura e não total, então
um servidor que entrega bytes devagar reseta o contador e o download nunca
estoura — corrigido com teto de tempo total explícito. E amarrar o status do
build à disponibilidade de um servidor de terceiro deixaria o badge vermelho toda
vez que o site da Câmara caísse, o que não diz nada sobre a qualidade do código.
A regeneração virou um fluxo separado, mensal e acionável à mão, porque a Câmara
atualiza o arquivo uma vez por mês e regenerar a cada push baixaria o mesmo dado
dezenas de vezes sem motivo.

**Recortar o arquivo real para usar como fixture de teste.** Traria nome de
deputado, CNPJ de fornecedor e CPF para dentro do repositório — exatamente o que
o projeto se propõe a não publicar. As seis linhas de teste são construídas à
mão em `tests/conftest.py`, cada uma com o motivo anotado ao lado.

## Estrutura

```
src/cota/
  esquema.py    as 32 colunas, o que é descartado e por quê
  limpar.py     funções puras: anonimização, classificação de CNPJ/CPF, valor efetivo
  fonte.py      download com cache e leitura em streaming do zip
  preparar.py   limpeza, filtro e o resumo auditável do que caiu
  analise.py    as seis perguntas, em SQL sobre DuckDB
  relatorio.py  geração do Markdown
  cli.py        preparar, relatorio, consultas
tests/          70 testes, 100% de cobertura, sem rede
relatorio/      saída gerada pelo fluxo mensal — não editar à mão
```

## Desenvolvimento

```bash
pytest --cov --cov-report=term-missing
ruff check . && ruff format --check .
```

O CI roda lint, formatação e a suíte com exigência de 90% de cobertura, em
Python 3.11, 3.12 e 3.13 — tudo sem rede. A regeneração do relatório é um fluxo
separado, mensal, que pode ser disparado à mão pela aba Actions.

## Fonte e licença

Dados: Câmara dos Deputados, arquivo anual da Cota para Exercício da Atividade
Parlamentar, publicado em `camara.leg.br/cotas` para reuso.

Código sob licença MIT. Ver [LICENSE](LICENSE).
