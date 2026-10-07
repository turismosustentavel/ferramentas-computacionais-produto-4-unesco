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
| 7 | Traça as rotas entre os pares origem-destino (TomTom Route Monitoring API) e guarda os vértices | `partida_chegada.csv` | `tomtom_routes.csv` |
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

As etapas 6 e 7 consultam serviços pagos. Se o arquivo que gravam já existe, a
esteira o usa e pula a consulta; só consulta de novo com `P4_REFAZER_COLETAS=1`.
Assim as etapas 8 e 9 rodam sem chave sobre os arquivos da coleta original, e
uma execução não apaga essa coleta. O `partida_chegada.csv`, entrada da etapa 7,
foi preparado fora da esteira; nenhuma etapa o gera.

## Onde ficam os arquivos

A esteira lê e grava tudo numa única pasta de trabalho, indicada pela variável
`P4_SELECAO_PONTOS` (sem ela, a pasta corrente). No acervo do projeto, os mesmos
arquivos estão organizados por etapa, dentro de
`Entregas/Produto 4/produção/Seleção dos pontos para aferição/final/`:

| Subpasta | Arquivos |
|---|---|
| `raw/` | entradas: `acessos.csv` (a etapa 1 o lê com o nome `acessos_inicio.csv`), `atrativos.csv`, `cnjps_dionisio.csv`, `cnpjs_municipios.csv` |
| `z_cleaned/` e `z_cleaned_merged/` | etapas 1 a 3 |
| `z_final_addressed/` | etapas 4 e 5 |
| `z_final_geocoded/` | etapa 6 e `partida_chegada.csv` |
| `z_rotas_tomtom/` | etapa 7 |
| `z_top_ranked/` | etapa 8 |

O `exportar_camadas.py` usa a mesma pasta de trabalho (`P4_SELECAO_PONTOS`). Procura
cada entrada primeiro solta na pasta, como a esteira grava, e depois nas subpastas
`final/z_top_ranked/` e `final/z_rotas_tomtom/` do acervo. Grava em `camadas_qgis/`,
dentro da mesma pasta.

## Entradas

| Arquivo | Conteúdo | Origem |
|---|---|---|
| `cnpjs_municipios.csv`, `cnjps_dionisio.csv` | Estabelecimentos das ACTs nos municípios do estudo | Cadastro Nacional da Pessoa Jurídica (Receita Federal) |
| `atrativos.csv`, `acessos_inicio.csv` | Atrativos e acessos de cada município, com coordenadas | Levantamento da equipe |
| `partida_chegada.csv` | Pares origem-destino: cada atrativo e o centro da área das ACTs do município | Construído a partir das bases acima |
| `traffic.csv` | Pontos de tráfego (`lat`, `lon`, `traffic`) | Base auxiliar da etapa 9; origem não registrada |
| `pontos_afericao_selecionados*.csv` | Pontos escolhidos, com justificativa (lido pelo exportador; sem `--csv`, o mais recente) | Decisão da equipe técnica |
| `ranked_by_frequency.csv` | Agrupamentos ordenados pela frequência (o exportador o prefere ao `top100_…`, quando existe) | Saída anterior da seleção |
| `atrativos_qualitativo_georeferenciado.csv` ou `atrativos_georeferenciados_limpo.csv` | Atrativos com a classificação do Produto 4 (camada 4 do exportador) | Levantamento da equipe |

Nenhuma dessas bases é distribuída neste repositório.

## Chaves

| Variável | Etapa |
|---|---|
| `GOOGLE_MAPS_API_KEY` | 6 |
| `TOMTOM_API_KEY` | 7 |
| `P4_REFAZER_COLETAS=1` | 6 e 7: consulta de novo mesmo que o arquivo exista |

As respostas da Google e da TomTom não são redistribuídas. Com chaves próprias e
`P4_REFAZER_COLETAS=1`, as etapas 6 e 7 geram novamente os arquivos, mas com o
estado dos serviços na data da execução, que não é o da coleta original. A chave só
é pedida quando a etapa realmente consulta o serviço; se a Google recusar a chave
ou a cota, a etapa 6 para sem gravar.

## O que não se reproduz por computador

A escolha final dos pontos foi feita pela equipe técnica sobre os agrupamentos,
com justificativa registrada para cada ponto. A hierarquia dos atrativos vem de
levantamento qualitativo (netnografia).
