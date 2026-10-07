# Análise por municípios

Ferramentas da análise dos doze municípios do estudo: coleta das bases municipais,
tratamento da pesquisa de campo, modelagem e cálculo dos indicadores. Os scripts
numerados são etapas executáveis; os módulos `*_p4.py` são bibliotecas usadas pelas
etapas e também podem ser executados sozinhos quando têm uma coleta própria.

Todos os caminhos partem de `P4_DADOS` (ver [`dados/README.md`](../dados/README.md)).
O que cada script lê e grava está no [mapa de dados](../docs/mapa_de_dados.md).

## Módulos de base

| Módulo | Conteúdo |
|---|---|
| `comum.py` | Registro canônico dos doze municípios (chave: código IBGE de 7 dígitos), normalização das grafias encontradas no acervo, leitura das coordenadas nos três formatos da planilha de campo, datas do Jotform, sistemas de referência e caminhos. |
| `bases_p4.py` | Malhas oficiais (municípios, UF, país, SNV, CIDE, reservatório de Itaipu), com as correções de superfície do SNV verificadas em campo. |
| `fichas_p4.py` | Leitura das quatro fichas de campo (Geral, Rodoviária, Aeroporto, Aduana): escalas, direção de cada escala, notas normalizadas, caracterização da via, itens de presença. |

## Ordem de execução

### 1. Bases municipais

| Script | O que faz |
|---|---|
| `08_extrair_ipardes.py` | Reduz as planilhas do IPARDES (PR) a formato longo e filtra os municípios do estudo. |
| `09_coletar_sidra_ibge.py` | Coleta, pela API do SIDRA/IBGE, a base municipal uniforme para os doze municípios (mesmo ano e mesmo método). |
| `10_coletar_mtur.py` | Coleta, no portal de dados abertos do Ministério do Turismo, o Mapa do Turismo, a categorização e o CADASTUR; guarda o arquivo nacional e o recorte dos doze. |
| `11_extrair_rais_turismo.py` | Agrega por município, por ACT e por sexo os vínculos formais no turismo (RAIS, conjunto do MTur). Depende do 10. |
| `35_coletar_mapa_turismo_vigente.py` | Consulta a categoria e a região turística no Mapa do Turismo vigente, pela mesma API do sítio do MTur. |

### 2. Pesquisa de campo

| Script | O que faz |
|---|---|
| `32_pontos_planejados_sem_coleta.py` | Registra os pontos previstos no plano de campo que não foram aferidos. |
| `02_atribuicao_espacial_pontos.py` | Atribui cada ponto ao município pela geometria (interseção com a malha municipal do IBGE). |
| `03_correcao_municipio_dos_pontos.py` | Aplica as regras de decisão sobre as divergências entre o município declarado em campo e o obtido pela geometria. Depende do 02. |
| `18_corrigir_camada_pontos.py` | Corrige, na camada consolidada, os registros que não correspondem ao levantado em campo. |
| `31_nomes_oficiais_pontos.py` | Leva para a camada consolidada o nome, a área de análise e a classificação turística de cada ponto, a partir da síntese de campo. Sem `--aplicar`, só confere. |
| `04_vinculo_fichas_pontos.py` | Liga cada ficha de campo ao ponto de aferição. |
| `06_diario_de_campo.py` | Reconstrói a sequência do levantamento a partir do carimbo de envio de cada ficha. |
| `20_verificar_distancias_fichas.py` | Confere as distâncias anotadas nas fichas contra a posição real (linha reta e malha viária). Depende do 04. |

### 3. Auditoria e perfil

| Script | O que faz |
|---|---|
| `01_auditoria_cobertura.py` | Matriz município × fonte (o que existe e o que falta em cada fonte do acervo) e lista das lacunas de cada município. |
| `12_montar_perfil_municipal.py` | Perfil consolidado de cada município, com a fonte de cada valor e as ausências declaradas. Depende de 01, 04, 09, 10, 11 e 32. |

### 4. Modelagem

Bibliotecas de cálculo, usadas pelas etapas seguintes:

| Módulo | O que calcula |
|---|---|
| `fluxos_p4.py` | Trajetos e agrupamentos dos vértices das rotas (frequência e sobreposição de trajetos). Depende da [seleção dos pontos](../selecao_pontos/README.md). |
| `atrativos_p4.py` | Hierarquia dos atrativos de cada município, casada com a camada georreferenciada. |
| `classe_via_p4.py` | Classe funcional (etiqueta `highway` do OpenStreetMap) da via em que cada ponto foi aferido. |
| `presencas_p4.py` | Presença e ausência dos itens avaliados em campo, por tema. |
| `conectividade_p4.py` | Indicadores da ANATEL (IBC e componentes) e presença das plataformas de aplicativo. |
| `trafego_p4.py` | Volume médio diário (PNCT/DNIT) por trecho do SNV e malha ferroviária. |
| `intermunicipal_p4.py` | Linhas estaduais de ônibus (DER-PR e AGEMS) com geometria sobre a rodovia. |
| `geckoapi_p4.py` | Coleta da oferta de ônibus da ClickBus pela GeckoAPI, com os destinos do DER-PR no Paraná, para a data em `GECKOAPI_DATA` (padrão: a data da coleta original, 30/09/2026, que só se reproduz sobre o cache). Grava um resumo por destino; os registros de oferta lidos pelos indicadores têm outro formato (ver [mapa de dados](../docs/mapa_de_dados.md)). |

Etapas que gravam as medidas por município, em `02_Dados_Municipais/<slug>/` (as
isócronas, em `02_Dados_Municipais/isocronas/<slug>/`); a ordem importa só onde
indicado:

| Etapa | O que calcula | Depende de |
|---|---|---|
| `23_isocronas_municipio.py` | Tempo de viagem por estrada a partir do município (Dijkstra sobre a malha principal do OpenStreetMap), como intervalo entre a velocidade-limite e a de circulação; tempos até os demais municípios, as cidades fronteiriças e as cidades de referência; extensão de via por faixa de tempo. | `fluxos_p4` |
| `localizacao_p4.py` | Posição no estado, distância à capital e à linha internacional, países vizinhos. | malhas oficiais |
| `deslocamento_interno_p4.py` | ACTs, atrativos, trajetos e sobreposição de fluxos dentro do município. | seleção dos pontos, 18, 31 |
| `avaliacao_pontos_p4.py` | Fichas de cada ponto aferido (notas, presenças, via) e médias por dimensão. | 04, 18, 31 |
| `contexto_p4.py` | Rodovias, tráfego, áreas protegidas, ônibus, malha aérea e náutica no entorno do município. Aceita os temas como argumento. | bases oficiais |

### 5. Indicadores

| Etapa | O que calcula | Depende de |
|---|---|---|
| `indicadores_perfil_p4.py` | Sete indicadores do perfil (população, grau de urbanização, PIB per capita, vínculos formais no turismo, vínculos por 100 habitantes, meios de hospedagem e agências no CADASTUR), com a posição de cada município entre os doze (empate recebe a mesma posição, a melhor); estrutura etária e valor adicionado por setor. | 12 |
| `indicadores_campo_p4.py` | Indicadores dos pontos aferidos: avaliação comparada, presenças e ausências, caracterização das vias, vias de chegada, rodoviária, aeroporto e aduanas. | `avaliacao_pontos_p4`, `deslocamento_interno_p4`, `contexto_p4` |
| `indicadores_municipais_p4.py` | Indicadores de acesso, mobilidade e conectividade: tempos por estrada, eixos rodoviários e tráfego, modos de chegada, ônibus (ligações, rede entre os municípios, baldeações, razão ônibus/carro), malha aérea, náutica, deslocamento interno e conectividade. | 23, `indicadores_perfil_p4`, `localizacao_p4`, `deslocamento_interno_p4`, `contexto_p4`, `avaliacao_pontos_p4` |

O cabeçalho de cada módulo de indicadores define cada indicador, os parâmetros e a
fonte.

## Variáveis de ambiente

| Variável | Usada por |
|---|---|
| `P4_DADOS` | todos |
| `GECKOAPI_KEYS` (ou `GECKOAPI_KEY`) | `geckoapi_p4.py` |
| `GECKOAPI_DATA` (AAAA-MM-DD) | `geckoapi_p4.py`; data já passada só funciona sobre o cache |

As consultas ao OpenStreetMap (Overpass, Nominatim, OSRM) não exigem chave.

## Como executar

Da raiz do repositório, com `P4_DADOS` definido:

```bash
python caderno_municipal/09_coletar_sidra_ibge.py
```

As saídas vão para `Caderno de informações por município/02_Dados_Municipais/` e
`00_Gestao/`, e as coletas de bases para as pastas do acervo indicadas no cabeçalho
de cada script. Duas etapas alteram uma entrada: `18` e `31` regravam a camada
`pontos_afericao_consolidados.geojson`; antes da primeira alteração, guardam uma
cópia em `pontos_afericao_consolidados_ORIGINAL.geojson`.
