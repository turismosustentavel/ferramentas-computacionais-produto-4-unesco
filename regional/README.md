# Diagnóstico regional: ferramentas de dados

Scripts de coleta, tratamento, modelagem e auditoria de dados do diagnóstico
regional de infraestrutura, mobilidade e conectividade do Produto 4 (projeto
UNESCO UNES 2369/2025, Itaipu Parquetec). A área de análise é a Faixa de
Fronteira do Paraná e de Mato Grosso do Sul.

Cada script começa com um cabeçalho que descreve o que ele faz, as entradas
(com a fonte), as saídas, as variáveis de ambiente e a forma de execução. Este
documento reúne essas informações e mostra como os módulos se encadeiam.

## Requisitos

- Python 3.11 ou superior (o projeto usou 3.12).
- Pacotes: `pandas`, `geopandas` (com `pyogrio`), `shapely` e `openpyxl`
  (leitura e gravação de XLSX).

## Caminhos e variáveis de ambiente

Nenhum script contém caminho absoluto. Todos importam as constantes de
[`_caminhos.py`](_caminhos.py):

| Constante  | Pasta                                                     |
|------------|-----------------------------------------------------------|
| `RAIZ`     | valor de `P4_DADOS`; sem a variável, `dados/` na raiz do repositório |
| `ENTREGAS` | `RAIZ/Entregas/Produto 4`                                 |
| `PRODUCAO` | `RAIZ/Entregas/Produto 4/produção`                        |
| `ACERVO`   | `RAIZ/Levantamentos e Análises/Produto 4`                 |

A árvore abaixo de `RAIZ` reproduz a pasta do convênio. Nas tabelas a seguir,
`produção/` abrevia `Entregas/Produto 4/produção/`.

| Variável         | Uso                                  | Obrigatória |
|------------------|--------------------------------------|-------------|
| `P4_DADOS`       | raiz da árvore de dados (todos os scripts) | não   |
| `TOMTOM_API_KEY` | chave da TomTom Traffic API (`02_monitoramento_trafego_tomtom/medidor_velocidades_reais_tomtom.py`) | sim, para esse script |

Os scripts são executados a partir da raiz do repositório:

```bash
python regional/<modulo>/<script>.py
```

## Módulos

### 01_onibus_terminais_clickbus — transporte rodoviário coletivo e terminais

| Script | O que faz |
|--------|-----------|
| `mapeador_terminais_rodoviarios.py` | Soma embarques e desembarques da bilhetagem da ANTT por município, cruza com o cadastro de terminais escrito no script, classifica cada terminal pelo total anual de passageiros e exporta a camada de terminais (GeoJSON, CSV, Shapefile e ZIP). |
| `analisador_linhas_e_vetores_onibus.py` | Calcula, sobre a bilhetagem da ANTT, o panorama geral, os pares origem-destino mais movimentados, a classificação dos fluxos em relação à Faixa de Fronteira (intra-faixa, chegada, saída, trânsito) e as rotas transfronteiriças; exporta o resumo por par origem-destino. |

### 02_monitoramento_trafego_tomtom — tráfego

| Script | O que faz |
|--------|-----------|
| `medidor_velocidades_reais_tomtom.py` | Consulta a TomTom Traffic API (Flow Segment Data) no ponto de cada porta e registra velocidade atual, velocidade de fluxo livre, razão entre as duas, perda percentual e classe de fluidez. O resultado depende do instante da consulta. |

### 03_deteccao_portas_fronteira_150km — portas de entrada na Faixa de Fronteira

| Script | O que faz |
|--------|-----------|
| `detector_e_clusterizador_portas_fronteira.py` | Grava a camada de portas federais a partir da lista escrita no script (GeoJSON em WGS 84 e Shapefile em SIRGAS 2000) e regrava a camada existente de portas estaduais nos mesmos dois formatos. |
| `mapeador_aduanas_e_travessias_internacionais.py` | Converte em camada de pontos o cadastro de travessias internacionais (pontes, aduanas, fronteira seca) escrito no script. |
| `mapeador_acessos_vicinais_e_rotas_informais_osm.py` | Reprojeta para SIRGAS 2000 e grava em Shapefile a camada de cruzamentos de vias vicinais do OpenStreetMap com o limite da faixa ou com a fronteira. A extração desses cruzamentos no OpenStreetMap foi feita antes e não está no repositório. |

### 05_malha_aerea_anac_siros — conectividade aérea

| Script | O que faz |
|--------|-----------|
| `pipeline_integrado_aviacao_anac.py` | Resume, por aeroporto de destino na Faixa de Fronteira, a soma de passageiros pagos, o número de rotas e as companhias aéreas, a partir da camada de rotas regulares da ANAC. |

### 08_utilitarios_auditoria_shapefiles — auditoria e exportação

| Script | O que faz |
|--------|-----------|
| `exportador_oficial_shapefiles_sirgas2000.py` | Converte a camada consolidada de portas de entrada de GeoJSON para Shapefile, com nomes de campo de até 10 caracteres, em SIRGAS 2000 e WGS 84, com arquivos `.cpg` em UTF-8. |

## Ordem de execução e dependências

A única dependência direta entre scripts é a do medidor de velocidades em
relação ao detector de portas: o medidor lê as camadas de portas da pasta
`12_portas_entrada_terrestres_oficiais_shp/`, onde o detector grava (ver
"Esquemas das camadas de portas", abaixo). Os demais scripts dependem apenas
de insumos externos.

```
insumos externos
   │
   ├── 03 detector_e_clusterizador_portas_fronteira ──► produção/12_…, 13_…, 14_…
   │        └──► 02 medidor_velocidades_reais_tomtom ──► produção/05_telemetria_…
   ├── 03 mapeador_aduanas_e_travessias_internacionais ──► produção/12_…
   ├── 03 mapeador_acessos_vicinais_e_rotas_informais_osm ──► produção/15_…
   ├── 01 mapeador_terminais_rodoviarios ──► produção/08_…
   ├── 01 analisador_linhas_e_vetores_onibus ──► produção/08_…
   ├── 05 pipeline_integrado_aviacao_anac ──► produção/09_…
   └── 08 exportador_oficial_shapefiles_sirgas2000 ──► produção/12_…
```

Ordem sugerida:

1. Módulo 03: `detector_e_clusterizador_portas_fronteira.py`, depois
   `mapeador_aduanas_e_travessias_internacionais.py` e
   `mapeador_acessos_vicinais_e_rotas_informais_osm.py`.
2. Módulo 02: `medidor_velocidades_reais_tomtom.py` (depois do detector).
3. Módulo 01: os dois scripts, em qualquer ordem.
4. Módulo 05: `pipeline_integrado_aviacao_anac.py`.
5. Módulo 08: `exportador_oficial_shapefiles_sirgas2000.py`.

### Esquemas das camadas de portas

Há duas versões das camadas de portas federais e estaduais, com esquemas
diferentes:

| Local | Campos | Lida por |
|-------|--------|----------|
| raiz de `produção/` | `id` numérico, `rodovias_str`, `uf`, `municipio`, `tipo_porta`, `tipo_pista`, `lat`, `lon` | `medidor_velocidades_reais_tomtom.py`, quando a pasta 12 não tem o arquivo |
| `produção/12_portas_entrada_terrestres_oficiais_shp/` (portas federais gravadas pelo detector) | `id` textual (`MS-01` a `MS-09`, `PR-01` a `PR-09`), `rodovia`, `uf`, `municipio`, `tipo_porta`, `pais_destino`, `tipo_pista`, `lat`, `lon` | `medidor_velocidades_reais_tomtom.py` |

O medidor aceita `id` textual ou numérico. O nome da rodovia ele lê do campo
`rodovias_str`; nas portas federais gravadas pelo detector o campo se chama
`rodovia`, e a coluna `rodovia` da saída do medidor sai como "Via Local". As
velocidades não dependem desse campo. Quando a consulta à TomTom falha, a porta
recebe 60 km/h com a classe "Fluidez Plena (Estimada)".

### Pastas de saída

O detector, o mapeador de vicinais, o mapeador de aduanas, o mapeador de
terminais, o medidor e o exportador criam as próprias pastas de saída. O
analisador do módulo 01 grava em
`produção/08_transporte_coletivo_rodoviarias_clickbus/`, que precisa existir.

## O que vai onde

### Entradas

| Arquivo | Pasta (relativa a `P4_DADOS`) | Fonte | Lido por |
|---------|-------------------------------|-------|----------|
| `cidades_fronteira_2025.xlsx` | `produção/08_transporte_coletivo_rodoviarias_clickbus/` | ANTT, conjunto "Monitriip Bilhetes de Passagem", extrato filtrado para os municípios de interesse: <https://dados.antt.gov.br/> | 01 `mapeador_terminais_…`, 01 `analisador_linhas_…` |
| `malha_rotas_aereas_regulares_anac.shp` | `produção/09_aviacao_rotas_e_aeroportos_anac/` | ANAC, voos regulares e passageiros pagos, preparados como camada de linhas: <https://www.gov.br/anac/pt-br/assuntos/dados-e-estatisticas> | 05 `pipeline_integrado_…` |
| `cruzamento_faixa_fronteira_rodovias_federais_pr_ms.geojson` | `produção/` (raiz) | Pontos de cruzamento das rodovias federais com o limite da faixa ou com a fronteira (camada preparada previamente) | 02 `medidor_…` (alternativa) |
| `cruzamento_faixa_fronteira_rodovias_estaduais_pr_ms.geojson` | `produção/` (raiz) | Idem, rodovias estaduais (DER-PR e AGESUL; camada preparada previamente) | 02 `medidor_…` (alternativa) |
| `cruzamento_faixa_fronteira_estradas_vicinais_osm.geojson` | `produção/` (raiz) ou `produção/12_portas_entrada_terrestres_oficiais_shp/` | Cruzamentos de vias vicinais do OpenStreetMap: <https://www.openstreetmap.org> | 02 `medidor_…`, 03 `mapeador_acessos_vicinais_…` |
| `14_portas_estaduais_30_pontos_shp.shp` | `produção/14_portas_estaduais_30_pontos_shp/` | Camada de portas estaduais existente (regravada pelo detector) | 03 `detector_…` |
| `portas_de_entrada_terrestres_faixa_fronteira.geojson` | `produção/` (raiz) | Camada consolidada de portas de entrada (preparada previamente) | 08 `exportador_oficial_…` |
| Flow Segment Data (consulta em linha) | — | TomTom Traffic API: <https://docs.tomtom.com/traffic-api/documentation/tomtom-maps/traffic-flow/flow-segment-data> | 02 `medidor_…` |

Os scripts `mapeador_terminais_rodoviarios.py` (cadastro de terminais),
`detector_e_clusterizador_portas_fronteira.py` (portas federais),
`mapeador_aduanas_e_travessias_internacionais.py` (travessias)
e `pipeline_integrado_aviacao_anac.py` (nomes dos aeroportos) trazem parte dos
dados escrita no próprio código.

### Saídas

| Arquivo | Pasta (relativa a `P4_DADOS`) | Gerado por | Lido por |
|---------|-------------------------------|------------|----------|
| `rodoviarias_faixa_fronteira_pr_ms.geojson`, `.csv`, `rodoviarias_faixa_fronteira_pr_ms_shp/`, `rodoviarias_faixa_fronteira_pr_ms_shp.zip` | `produção/08_transporte_coletivo_rodoviarias_clickbus/` | 01 `mapeador_terminais_…` | — |
| `resumo_analise_linhas_vetores_onibus.csv` | `produção/08_transporte_coletivo_rodoviarias_clickbus/` | 01 `analisador_linhas_…` | — |
| `fluxo_tomtom_portas_federais_faixa_5km.csv`, `fluxo_tomtom_portas_estaduais_faixa_5km.csv`, `fluxo_tomtom_estradas_vicinais_faixa_5km.csv` | `produção/05_telemetria_velocidades_reais_tomtom/` | 02 `medidor_…` | — |
| `cruzamento_faixa_fronteira_rodovias_federais_pr_ms.geojson`, `cruzamento_faixa_fronteira_rodovias_estaduais_pr_ms.geojson` | `produção/12_portas_entrada_terrestres_oficiais_shp/` | 03 `detector_…` | 02 `medidor_…`; 03 `detector_…` (estaduais, na falta do Shapefile da pasta 14) |
| `13_portas_federais_18_pontos_shp.shp` | `produção/13_portas_federais_18_pontos_shp/` | 03 `detector_…` | — |
| `14_portas_estaduais_30_pontos_shp.shp` | `produção/14_portas_estaduais_30_pontos_shp/` | 03 `detector_…` | 03 `detector_…` |
| `travessias_internacionais_aduanas.geojson` | `produção/12_portas_entrada_terrestres_oficiais_shp/` | 03 `mapeador_aduanas_…` | — |
| `15_portas_vicinais_nao_pavimentadas_osm_shp.shp` | `produção/15_portas_vicinais_nao_pavimentadas_osm_shp/` | 03 `mapeador_acessos_vicinais_…` | — |
| `tabela_resumo_movimentacao_aeroportos_anac.csv` | `produção/09_aviacao_rotas_e_aeroportos_anac/` | 05 `pipeline_integrado_…` | — |
| `portas_de_entrada_terrestres_SIRGAS2000.shp`, `portas_de_entrada_terrestres_WGS84.shp` (com `.cpg`) | `produção/12_portas_entrada_terrestres_oficiais_shp/` | 08 `exportador_oficial_…` | — |

## Fora deste repositório

Partes do diagnóstico regional que o Produto 4 usa, mas cujo código não está aqui:
a modelagem das isócronas regionais, a extração dos cruzamentos de vias vicinais
no OpenStreetMap e a preparação das tabelas de ônibus da pasta
`produção/08_transporte_coletivo_rodoviarias_clickbus/` lidas pela análise por
municípios (ver [mapa de dados](../docs/mapa_de_dados.md)).
