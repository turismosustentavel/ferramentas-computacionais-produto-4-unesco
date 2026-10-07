# Mapa de dados

O que cada ferramenta lê, de onde vem e onde grava. Os caminhos são relativos à raiz
dos dados (`P4_DADOS`; ver [`dados/README.md`](../dados/README.md)). Abreviações:

- `acervo/` = `Levantamentos e Análises/Produto 4/`
- `produção/` = `Entregas/Produto 4/produção/`
- `caderno/` = `Entregas/Produto 4/produção/Caderno de informações por município/`
- `<slug>` = pasta do município em `comum.MUNICIPIOS` (por exemplo `01_Foz_do_Iguacu_PR`)

As tabelas completas das outras duas partes estão em:

- [`selecao_pontos/README.md`](../selecao_pontos/README.md) — seleção dos pontos de aferição;
- [`regional/README.md`](../regional/README.md) — diagnóstico regional.

---

## Análise por municípios (`caderno_municipal/`)

### Bases oficiais

| Arquivo | Pasta | Conteúdo e fonte | Lido por |
|---|---|---|---|
| `BR_Municipios_2025.zip`, `BR_UF_2025.zip`, `BR_Pais_2025.zip` | `acervo/01_Bases_Secundarias_Oficiais/Shapes/` | Malhas territoriais do IBGE, edição 2025 | `bases_p4`, 02, 03 |
| `vw_dif_ferrovias.zip` | idem | Malha ferroviária, base geográfica do DNIT | `trafego_p4`, `contexto_p4` |
| `vw_snv_rod.shp` | `produção/02_malha_rodoviaria_nacional_dnit_snv_shp/` | Sistema Nacional de Viação, DNIT | `bases_p4`, 03 |
| `vw_cide_rod_2021.shp` | `produção/03_malha_rodoviaria_pavimentacao_dnit_cide_shp/` | Malha rodoviária com pavimentação (base CIDE 2021), DNIT | `bases_p4` |
| `malha_fluxo_pnct_2025_oficial.geojson` | `acervo/05_Telemetria_e_BigData/DNIT_PNCT_Trafego/` | Plano Nacional de Contagem de Tráfego, DNIT, 2025 | `trafego_p4` |
| `Zoneamento_FP_Reserv.shp` | `acervo/08_Infraestrutura_e_Turismo_Nautico/01_Vetores_e_Rotas_Nauticas/Zoneamento_Altimetria/` | Espelho d'água do reservatório de Itaipu (zoneamento) | `bases_p4` |
| `consolidado_final_01_09_2026.csv` | `produção/08_transporte_coletivo_rodoviarias_clickbus/` | Bilhetagem do transporte interestadual (ANTT, Monitriip), extrato de 01/09/2026 | `geckoapi_p4`, `contexto_p4` |
| planilhas do IPARDES (`*.csv`, UTF-16) | `acervo/09_Base_Socioeconomica_Municipal/01_IPARDES_PR_bruto/` | Base de Dados do Estado, IPARDES (PR), baixada do portal | 08 |
| `vw_icmbio_unid_conserv.zip`, `vw_funai_terras_indigenas.zip`, `vw_iphan_sitios_arq.zip` | `acervo/01_Bases_Secundarias_Oficiais/Shapes/` | Unidades de conservação (ICMBio), terras indígenas (FUNAI) e sítios arqueológicos (IPHAN) | `contexto_p4` |
| `vw_antaq_travessias.zip`, `vw_antaq_portos.zip`, `vw_antaq_vias_navegaveis.zip` | idem | Travessias, portos e vias navegáveis (ANTAQ) | `contexto_p4` |

Coletadas pelos próprios scripts:

| Fonte | Endereço | Script | Grava em |
|---|---|---|---|
| SIDRA/IBGE | `https://apisidra.ibge.gov.br` | 09 | `acervo/09_Base_Socioeconomica_Municipal/03_IBGE_SIDRA/` |
| Dados abertos do MTur (CKAN): Mapa do Turismo, categorização, CADASTUR, empregos formais no turismo (RAIS) | `https://dados.turismo.gov.br` | 10, 11 | `acervo/09_Base_Socioeconomica_Municipal/08_MTur_Dados_Abertos/` |
| Mapa do Turismo vigente | `https://www.mapa.turismo.gov.br` | 35 | idem |
| OpenStreetMap (Overpass API) | `https://overpass-api.de` | `classe_via_p4`, 20, 23 | caches (ver abaixo) |
| Nominatim e OSRM (OpenStreetMap) | `https://nominatim.openstreetmap.org`, `http://router.project-osrm.org` | 20 | `caderno/02_Dados_Municipais/cache/` |
| ClickBus via GeckoAPI | `https://api.geckoapi.com.br` | `geckoapi_p4` | `caderno/02_Dados_Municipais/oferta_clickbus/consulta_geckoapi_<slug>.json` |

### Insumos preparados fora deste repositório

Tabelas e camadas montadas no diagnóstico regional ou pela equipe, a partir de fontes
oficiais ou de consultas, cujo processo de preparação não está neste repositório.

| Arquivo | Pasta | Conteúdo | Lido por |
|---|---|---|---|
| `linhas_onibus_intra_faixa_fronteira.geojson` | `produção/11_transporte_regional_intra_faixa/` | Linhas estaduais de ônibus (registros do DER-PR e da AGEMS) desenhadas sobre a rodovia | `intermunicipal_p4` |
| `malha_fluxo_veiculos_vdm.geojson` | `acervo/05_Telemetria_e_BigData/DNIT_PNCT_Trafego/` | Volume médio diário por trecho, com campos de porta de entrada e perfil de tráfego que não vêm do PNCT; origem não registrada | `trafego_p4` |
| `Dados conectividade - Fronteira.xlsx` | `acervo/06_Dados_Processados_Pipeline/Planilhas_Consolidadas/` | Indicadores da ANATEL (Índice Brasileiro de Conectividade e componentes) reunidos com a presença de plataformas de aplicativo | `conectividade_p4` |
| `malha_rotas_aereas_regulares_anac.geojson` | `produção/09_aviacao_rotas_e_aeroportos_anac/` | Rotas aéreas regulares e passageiros pagos (dados da ANAC), preparadas como camada de linhas | `contexto_p4` |
| `rotas_ocean_eyes.geojson`, `catalogo_waypoints_unicos.csv` | `acervo/08_Infraestrutura_e_Turismo_Nautico/01_Vetores_e_Rotas_Nauticas/` | Proposta de roteirização náutica (acervo Ocean Eyes) e catálogo de pontos de passagem | `contexto_p4` |
| `america_do_sul_paises.gpkg` | `acervo/09_Base_Socioeconomica_Municipal/06_Cartografia_Tematica/` | Países da América do Sul (campos `PAIS` e `FIPS_CNTRY`); fonte não registrada | `localizacao_p4` |
| `tabela_diferenciacao_rotas_terminais_fronteira.csv`, `tabela_trechos_inbound_portas_entrada_onibus.csv` | `produção/08_transporte_coletivo_rodoviarias_clickbus/` | Destinos dos terminais e trechos de chegada pelas portas de entrada, do diagnóstico regional | `contexto_p4` |
| `amostra_rotas_oferta_onibus_clickbus_faixa_fronteira.csv` | idem | Amostra de oferta de ônibus do diagnóstico regional | `contexto_p4` (o resultado entra em `indicadores_municipais_p4` quando falta o registro de oferta do município) |

### Pesquisa de campo e decisões da equipe

Nada disto é distribuído: as fichas contêm dados pessoais da equipe de campo.

| Arquivo | Pasta | Conteúdo | Lido por |
|---|---|---|---|
| `Formulário_Geral_-_Produto_04*.csv`, `Formulário_Rodoviárias_*`, `Formulário_Aeroportos_*`, `Formulário_Aduanas_*` | `acervo/03_Pesquisa_de_Campo_Primaria/01_Jotform_Bruto/` | Exportação das quatro fichas aplicadas em campo (Jotform) | `fichas_p4`, 01, 04, 06 |
| `georreferenciamento.xlsx` | idem | Planejamento de campo: pontos previstos e coordenadas | 02, 04, 32 |
| `pontos_afericao_selecionados.csv` | `acervo/03_Pesquisa_de_Campo_Primaria/03_Pontos_Afericao/` | Pontos de aferição escolhidos | 01, 02 |
| `pontos_afericao_consolidados.geojson` | `acervo/03_Pesquisa_de_Campo_Primaria/03_Pontos_Afericao/vetores_gis/` | Camada consolidada dos pontos (ordem, categoria, formulário aplicado) | 04, 18, 20, 31, `deslocamento_interno_p4`, `avaliacao_pontos_p4` |
| `Dados Pesquisa de campo 4.2 Unesco.csv.xlsx` | `acervo/03_Pesquisa_de_Campo_Primaria/03_Pontos_Afericao/` | Síntese de campo (aba "síntese pontos de coleta") | 31 |
| `1_pontos_afericao_selecionados.geojson` | `acervo/06_Dados_Processados_Pipeline/CNPJs_e_Atrativos_Clusters/camadas_qgis/` | Camada exportada pela [seleção dos pontos](../selecao_pontos/README.md) | 01, 02 |
| `4_atrativos_turisticos.geojson` | idem | Atrativos georreferenciados, com o posto na hierarquia (`RANK_PROD4`) | `deslocamento_interno_p4` |
| `cnpjs_georreferenciados.csv` | `acervo/06_Dados_Processados_Pipeline/CNPJs_e_Atrativos_Clusters/z_final_geocoded/` | Estabelecimentos das ACTs geocodificados pela seleção dos pontos | `deslocamento_interno_p4` |
| `correcoes_atrativos.json` (opcional) | `caderno/02_Dados_Municipais/atrativos/` | Correções de coordenada, exclusões e exceções de atrativos, com a fonte de cada uma | `deslocamento_interno_p4` |
| `tomtom_routes.csv` | `produção/Seleção dos pontos para aferição/final/z_rotas_tomtom/` | Vértices das rotas TomTom da seleção dos pontos | `fluxos_p4`, `deslocamento_interno_p4`, 23 |
| `Atrativos_Relevantes_Por_Cidade.md` | `produção/Seleção dos pontos para aferição/` | Hierarquia dos atrativos (levantamento qualitativo) | `atrativos_p4`, 01 |
| `plataformas_listas_oficiais.json` | `caderno/02_Dados_Municipais/plataformas/` | Conferência da presença de plataformas nas listas oficiais de cidades atendidas (29/09/2026) | `conectividade_p4` |
| `consulta_linhas_der_pr.json`, `linhas_detalhe_der_pr.json` | `caderno/02_Dados_Municipais/der_pr/` | Registro da consulta às linhas do DER-PR por município (24/09/2026) | `geckoapi_p4` |
| `oferta_clickbus_<slug>.json`, `rede_do_estudo_<slug>.json`, `pernas_<slug>.json` | `caderno/02_Dados_Municipais/oferta_clickbus/` | Registro da oferta de ônibus: partidas por destino em 30/09/2026 (quarta-feira) e 03/10/2026 (sábado), consultadas na ClickBus pela GeckoAPI, com os grupos de destinos; ligações entre os municípios do estudo; trechos das viagens com baldeação (página pública da ClickBus, 24/09/2026). A montagem desses registros não está neste repositório: o `geckoapi_p4` faz a consulta de uma data e grava outro arquivo, mais simples | `indicadores_municipais_p4` |

O inventário (01) também confere a existência de material de campo que não é lido em
conteúdo: fichas preenchidas em `acervo/03_Pesquisa_de_Campo_Primaria/02_Fichas_Preenchidas/`,
fotos e anotações em `Entregas/Produto 4/Entrega 4.3/`, entrevistas em
`acervo/04_Entrevistas_e_Qualitativo/` e fichas náuticas em
`acervo/08_Infraestrutura_e_Turismo_Nautico/03_Checklists_e_Fichas_Municipais/`.

### Saídas

| Arquivo | Pasta | Gravado por | Lido por |
|---|---|---|---|
| `ipardes_series_longas_municipios_estudo.csv`, `.xlsx` | `acervo/09_Base_Socioeconomica_Municipal/02_Extracoes_12_municipios/` | 08 | — |
| `sidra_<tabela>.csv`, `sidra_base_municipal.xlsx`, `procedencia.json` | `acervo/09_Base_Socioeconomica_Municipal/03_IBGE_SIDRA/` | 09 | 12 |
| `nacional/`, `recorte_12/`, `resumo_da_coleta.csv`, `procedencia.json` | `acervo/09_Base_Socioeconomica_Municipal/08_MTur_Dados_Abertos/` | 10 | 11, 12 |
| `rais_turismo/rais_turismo_2025_por_{municipio,act,sexo}.csv` | idem | 11 | 12 |
| `nacional/mapa_turismo_vigente_<ano>.csv`, `recorte_12/mapa_turismo_vigente.json` | idem | 35 | — |
| `pontos_planejados_sem_coleta.json` | `acervo/03_Pesquisa_de_Campo_Primaria/03_Pontos_Afericao/` | 32 | 12 |
| `pontos_atribuicao_espacial.xlsx`, `.geojson` | `caderno/02_Dados_Municipais/` | 02 | 03 |
| `pontos_municipio_corrigido.xlsx`, `.geojson` | idem | 03 | — |
| `pontos_afericao_consolidados.geojson` (regravado; cópia `_ORIGINAL`) | `acervo/03_Pesquisa_de_Campo_Primaria/03_Pontos_Afericao/vetores_gis/` | 18, 31 | 04, 20, `deslocamento_interno_p4`, `avaliacao_pontos_p4` |
| `vinculo_fichas_pontos.xlsx` | `caderno/02_Dados_Municipais/` | 04 | 12, 20, `avaliacao_pontos_p4` |
| `diario_de_campo.xlsx` | idem | 06 | — |
| `verificacao_distancias_fichas.xlsx`, `.json` | idem | 20 | — |
| `auditoria_cobertura.xlsx` (matriz), `auditoria_cobertura.md` (lacunas por município) | `caderno/00_Gestao/` | 01 | 12 (o `.xlsx`) |
| `<slug>/perfil_municipal.json`, `perfis_municipais.xlsx` | `caderno/02_Dados_Municipais/` | 12 | `indicadores_perfil_p4`, `indicadores_municipais_p4` |
| `oferta_clickbus/consulta_geckoapi_<slug>.json` | idem | `geckoapi_p4` | — |
| `isocronas/<slug>/isocronas_<slug>.geojson`, `tempos_<slug>.csv`, `metricas_isocronas_<slug>.json` | idem | 23 | `indicadores_municipais_p4` |
| `<slug>/metricas_situacao_<slug>.json` | idem | `localizacao_p4` | `indicadores_municipais_p4` |
| `<slug>/metricas_deslocamento_<slug>.json`, `<slug>/camadas_internas_<slug>.gpkg` | idem | `deslocamento_interno_p4` | `indicadores_municipais_p4`, `indicadores_campo_p4` |
| `<slug>/fichas_<slug>.json`, `<slug>/metricas_matrizes_<slug>.json` | idem | `avaliacao_pontos_p4` | `indicadores_campo_p4`, `indicadores_municipais_p4` |
| `<slug>/metricas_contexto_<slug>.json` | idem | `contexto_p4` | `indicadores_municipais_p4`, `indicadores_campo_p4` |
| `indicadores_perfil.csv`, `.xlsx`; `<slug>/metricas_perfil_<slug>.json` | idem | `indicadores_perfil_p4` | `indicadores_municipais_p4` |
| `indicadores_campo.xlsx` | idem | `indicadores_campo_p4` | — |
| `indicadores_municipais.xlsx` | idem | `indicadores_municipais_p4` | — |

As saídas sem leitor ("—") são registros finais ou de conferência.

### Caches

Respostas de serviços guardadas para não consultar de novo. Apagar o arquivo força uma
nova consulta, com o estado do serviço na data.

| Cache | Pasta | Gravado por |
|---|---|---|
| `osm_isocronas_<slug>/bloco_<lat>_<lon>.json` | `caderno/02_Dados_Municipais/cache/` | 23 |
| `osm_classe_via_<slug>.json` | idem | `classe_via_p4` |
| `geocodificacao_referencias.json` | idem | 20 |
| `geckoapi/` | idem | `geckoapi_p4` |
