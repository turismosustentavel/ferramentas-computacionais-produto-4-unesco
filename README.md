# Ferramentas computacionais do Produto 4 – UNESCO

Ferramentas de coleta, tratamento, modelagem e cálculo de indicadores usadas no
Produto 4 do projeto UNESCO UNES 2369/2025, executado pelo Itaipu Parquetec:
diagnóstico de infraestrutura, mobilidade e conectividade do turismo nos municípios
da faixa de fronteira do Paraná, de Santa Catarina e de Mato Grosso do Sul.

O repositório contém o código e a documentação do método. Não contém dados, resultados,
tabelas de indicadores nem camadas: cada script diz o que lê, de onde vem e onde grava,
e o [mapa de dados](docs/mapa_de_dados.md) reúne tudo isso num só lugar.

## Estrutura

```
├── selecao_pontos/       seleção dos pontos de aferição em campo
├── regional/             diagnóstico regional: ônibus e terminais, tráfego, portas
│                         de fronteira, isócronas, aviação, auditoria de camadas
├── caderno_municipal/    análise por municípios: bases municipais, pesquisa de
│                         campo, modelagem e indicadores
├── docs/                 mapa de dados e ordem de execução
├── dados/                raiz padrão dos dados (vazia; ver dados/README.md)
├── requirements.txt
└── .env.example          variáveis de ambiente (chaves e pastas)
```

Cada pasta tem um README com o que cada script faz, a ordem de execução e as
dependências entre etapas.

## Fluxo geral

```
  bases oficiais ──────────────┐
  (IBGE, MTur, RAIS, DNIT,     │
   ANAC, ANATEL, IPARDES,      ▼
   DER-PR, AGEMS, OSM)    regional/  ──────────────┐
                                                   │
  CNPJ + atrativos ──► selecao_pontos/ ──► campo ──┤
                       (rotas TomTom,     (fichas  │
                        agrupamento)       Jotform)▼
                                          caderno_municipal/
                                          indicadores por município
```

A [ordem de execução](docs/ordem_de_execucao.md) detalha a sequência.

## Instalação

Python 3.11 ou superior.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/macOS
pip install -r requirements.txt
```

## Configuração

1. **Dados.** Defina `P4_DADOS` com a pasta onde estão os dados, organizada como
   descrito em [`dados/README.md`](dados/README.md). Sem a variável, os scripts
   procuram em `dados/`.
2. **Chaves.** As coletas em serviços comerciais (Google, TomTom, ClickBus, GeckoAPI)
   pedem chave própria, sempre por variável de ambiente. Copie `.env.example` para
   `.env` ou defina as variáveis no sistema. Nenhuma chave acompanha o repositório.

## O que se reproduz e o que não se reproduz

- **Bases oficiais** (IBGE, MTur, RAIS, DNIT, ANAC, ANATEL, IPARDES, OpenStreetMap):
  os scripts de coleta baixam de novo as edições publicadas, que podem ter sido
  atualizadas desde a coleta original. As coletas do SIDRA e do MTur registram a
  data em `procedencia.json`.
- **Serviços comerciais** (geocodificação da Google, rotas e velocidades da TomTom,
  oferta da ClickBus): as respostas não são redistribuídas. Com chave própria, os
  scripts consultam de novo, mas o resultado reflete o estado do serviço na data da
  execução.
- **Pesquisa de campo**: as fichas registram as condições observadas no momento da
  visita e contêm dados pessoais da equipe; não são distribuídas. Os scripts
  documentam como elas foram lidas e tratadas.
- **Juízo técnico**: a escolha final dos pontos de aferição foi feita pela equipe
  técnica, com justificativa registrada para cada ponto, e a hierarquia dos atrativos
  resulta de levantamento qualitativo.
