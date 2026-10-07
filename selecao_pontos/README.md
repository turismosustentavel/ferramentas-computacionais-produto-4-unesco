# Seleção dos pontos de aferição

Etapa que antecede o campo. Cruza a localização dos estabelecimentos das
Atividades Características do Turismo (ACTs) e dos atrativos com as rotas viárias
reais entre eles e identifica os trechos de maior sobreposição de fluxos. Sobre
esses agrupamentos, a equipe escolheu os pontos aferidos em campo e registrou a
justificativa de cada um.

## Arquivos

| Arquivo | O que faz |
|---|---|
| `selecao_pontos_afericao.py` | Esteira completa, da limpeza das bases ao agrupamento dos vértices das rotas. |
| `exportar_camadas.py` | Converte os pontos escolhidos, os agrupamentos, as rotas e os atrativos em camadas vetoriais (GeoPackage, GeoJSON e Shapefile). |

## Etapas da esteira

| # | Etapa | Lê | Grava |
|---|---|---|---|
| 1 | Separa a coordenada dos acessos em latitude e longitude | `acessos_inicio.csv` | `acessos.csv` |
| 2 | Une as bases de CNPJ | `cnpjs_municipios.csv`, `cnjps_dionisio.csv` | `cnpjs.csv` |
| 3 | Une atrativos e acessos | `atrativos.csv`, `acessos.csv` | `atrativos_acessos.csv` |
| 4 | Monta o endereço completo de cada CNPJ | `cnpjs.csv` | `cnpjs_enderecos.csv` |
| 5 | Amostra de 50% dos CNPJs (identificadores pares) | `cnpjs_enderecos.csv` | `cnpjs_enderecos_compressed.csv` |
| 6 | Geocodifica os endereços (Google Geocoding API) | `cnpjs_enderecos_compressed.csv` | `cnpjs_georreferenciados.csv` |
| 7 | Traça as rotas entre os pares origem-destino (TomTom Routing API) e guarda os vértices | `partida_chegada.csv` | `tomtom_routes.csv` |
| 8 | Agrupa os vértices por DBSCAN (haversine) em cada município e ordena pela frequência | `tomtom_routes.csv` | `top100_clusters_per_city_r100.csv` |
| 9 | Combina a frequência com uma base de pontos de tráfego, em raio de 50 m, com pesos iguais | `top100_clusters_per_city_r100.csv`, `traffic.csv` | `ranked_points.csv` |

**Parâmetros aplicados**

- Amostra dos CNPJs: 50%, identificadores pares.
- Agrupamento: DBSCAN com métrica haversine, `EPS_METERS = 100`, `TOP_N = 100` por
  município. O arquivo `top20_clusters_per_city_r50.csv` corresponde, pelo nome, a
  `EPS_METERS = 50` e `TOP_N = 20`.
- A **frequência** de um agrupamento é o número de vértices de rota que caem nele.
  É uma medida de densidade de vértices, não do número de trajetos distintos que
  passam pelo ponto. O módulo `caderno_municipal/fluxos_p4.py` calcula as duas.

## Onde ficam os arquivos

A esteira lê e grava tudo numa única pasta de trabalho, indicada pela variável
`P4_SELECAO_PONTOS` (sem ela, a pasta corrente). No acervo do projeto, os mesmos
arquivos estão organizados por etapa, dentro de
`Entregas/Produto 4/produção/Seleção dos pontos para aferição/final/`:

| Subpasta | Arquivos |
|---|---|
| `raw/` | entradas: `acessos.csv`, `atrativos.csv`, `cnjps_dionisio.csv`, `cnpjs_municipios.csv` |
| `z_cleaned/` e `z_cleaned_merged/` | etapas 1 a 3 |
| `z_final_addressed/` | etapas 4 e 5 |
| `z_final_geocoded/` | etapa 6 e `partida_chegada.csv` |
| `z_rotas_tomtom/` | etapa 7 |
| `z_top_ranked/` | etapa 8 |

O `exportar_camadas.py` roda na pasta `Seleção dos pontos para aferição/` e grava
em `camadas_qgis/`.

## Entradas

| Arquivo | Conteúdo | Origem |
|---|---|---|
| `cnpjs_municipios.csv`, `cnjps_dionisio.csv` | Estabelecimentos das ACTs nos municípios do estudo | Cadastro Nacional da Pessoa Jurídica (Receita Federal) |
| `atrativos.csv`, `acessos_inicio.csv` | Atrativos e acessos de cada município, com coordenadas | Levantamento da equipe |
| `partida_chegada.csv` | Pares origem-destino: cada atrativo e o centro da área das ACTs do município | Construído a partir das bases acima |
| `traffic.csv` | Pontos de tráfego (`lat`, `lon`, `traffic`) | Base auxiliar da etapa 9 |
| `pontos_afericao_selecionados*.csv` | Pontos escolhidos, com justificativa | Decisão da equipe técnica |

Nenhuma dessas bases é distribuída neste repositório.

## Chaves

| Variável | Etapa |
|---|---|
| `GOOGLE_MAPS_API_KEY` | 6 |
| `TOMTOM_API_KEY` | 7 |

As respostas da Google e da TomTom não são redistribuídas. Com chaves próprias, as
etapas 6 e 7 geram novamente os arquivos, mas com o estado dos serviços na data da
execução, que não é o da coleta original.

## O que não se reproduz por computador

A escolha final dos pontos foi feita pela equipe técnica sobre os agrupamentos,
com justificativa registrada para cada ponto. A hierarquia dos atrativos vem de
levantamento qualitativo (netnografia).
