# Ordem de execução

Sequência completa, da seleção dos pontos aos indicadores por município. Cada etapa só
precisa rodar de novo quando uma entrada dela muda. Os comandos partem da raiz do
repositório, com `P4_DADOS` definido.

## 1. Seleção dos pontos de aferição

Antes do campo. Detalhes em [`selecao_pontos/README.md`](../selecao_pontos/README.md).
As duas ferramentas usam a pasta de trabalho indicada em `P4_SELECAO_PONTOS`.

```bash
python selecao_pontos/selecao_pontos_afericao.py
python selecao_pontos/exportar_camadas.py
```

Entre uma e outra, a equipe escolhe os pontos sobre os agrupamentos e registra a
justificativa de cada um (`pontos_afericao_selecionados*.csv`). As etapas que
consultam a Google e a TomTom usam os arquivos já gravados; só consultam de novo com
`P4_REFAZER_COLETAS=1`.

## 2. Diagnóstico regional

Independente da análise por municípios, salvo pelas camadas e tabelas que ela lê da
pasta `produção/`. Detalhes em [`regional/README.md`](../regional/README.md).

1. `regional/03_deteccao_portas_fronteira_150km/` — portas de entrada.
2. `regional/02_monitoramento_trafego_tomtom/medidor_velocidades_reais_tomtom.py` — depois das portas.
3. `regional/01_onibus_terminais_clickbus/`, `05_malha_aerea_anac_siros/`,
   `08_utilitarios_auditoria_shapefiles/` — em qualquer ordem.

## 3. Análise por municípios

Detalhes em [`caderno_municipal/README.md`](../caderno_municipal/README.md). Os blocos
rodam de cima para baixo.

```
 bases municipais         08 · 09 · 10 → 11 · 35 · 32

 pesquisa de campo        02 → 03
                          18 → 31 → 04 → 20
                          06

 auditoria e perfil       01 → 12            (o 12 lê também 04, 09, 10, 11 e 32)

 medidas por município    23 · localizacao_p4 · deslocamento_interno_p4
                          avaliacao_pontos_p4 · contexto_p4

 indicadores              indicadores_perfil_p4       (lê o 12)
                          indicadores_campo_p4        (lê avaliacao, deslocamento, contexto)
                          indicadores_municipais_p4   (lê o 12, o 23, indicadores_perfil
                                                       e as medidas por município)
```

`→` indica dependência; `·` separa etapas independentes entre si.

Em comandos:

```bash
# bases municipais
python caderno_municipal/08_extrair_ipardes.py
python caderno_municipal/09_coletar_sidra_ibge.py
python caderno_municipal/10_coletar_mtur.py
python caderno_municipal/11_extrair_rais_turismo.py
python caderno_municipal/35_coletar_mapa_turismo_vigente.py
python caderno_municipal/32_pontos_planejados_sem_coleta.py

# pesquisa de campo
python caderno_municipal/02_atribuicao_espacial_pontos.py
python caderno_municipal/03_correcao_municipio_dos_pontos.py
python caderno_municipal/18_corrigir_camada_pontos.py
python caderno_municipal/31_nomes_oficiais_pontos.py            # confere
python caderno_municipal/31_nomes_oficiais_pontos.py --aplicar  # grava
python caderno_municipal/04_vinculo_fichas_pontos.py
python caderno_municipal/20_verificar_distancias_fichas.py
python caderno_municipal/06_diario_de_campo.py

# auditoria e perfil
python caderno_municipal/01_auditoria_cobertura.py
python caderno_municipal/12_montar_perfil_municipal.py

# medidas por município (um ou mais slugs; ver comum.MUNICIPIOS)
python caderno_municipal/23_isocronas_municipio.py 01_Foz_do_Iguacu_PR
python caderno_municipal/localizacao_p4.py 01_Foz_do_Iguacu_PR
python caderno_municipal/deslocamento_interno_p4.py 01_Foz_do_Iguacu_PR
python caderno_municipal/avaliacao_pontos_p4.py 01_Foz_do_Iguacu_PR
python caderno_municipal/contexto_p4.py 01_Foz_do_Iguacu_PR

# indicadores
python caderno_municipal/indicadores_perfil_p4.py
python caderno_municipal/indicadores_campo_p4.py
python caderno_municipal/indicadores_municipais_p4.py
```

## Coletas que dependem da data

- As coletas de bases oficiais (09, 10, 35) baixam a edição publicada no dia.
- O `geckoapi_p4` consulta a oferta de ônibus na data de `GECKOAPI_DATA` (padrão: a
  da coleta original). Data já passada só se lê do cache; sem cache, a execução para.
  Ele grava um resumo à parte e não substitui os registros de oferta lidos pelos
  indicadores (ver [mapa de dados](mapa_de_dados.md)).
- As consultas ao OpenStreetMap (20, 23, `classe_via_p4`) usam o cache quando existe.

Para refazer as contas sobre os mesmos dados da coleta original, use os arquivos já
gravados e os caches, e não rode as coletas.
