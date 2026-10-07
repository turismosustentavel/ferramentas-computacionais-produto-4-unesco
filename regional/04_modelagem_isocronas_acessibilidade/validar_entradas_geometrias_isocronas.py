# -*- coding: utf-8 -*-
"""
================================================================================
PROJETO UNESCO UNES 2369/2025 | ITAIPU PARQUETEC - TS.DTUR
PRODUTO 4: DIAGNÓSTICO REGIONAL DE INFRAESTRUTURA, MOBILIDADE E CONECTIVIDADE
================================================================================
MÓDULO 04: MODELAGEM DE ACESSIBILIDADE E ISÓCRONAS
SCRIPT: validar_entradas_geometrias_isocronas.py
--------------------------------------------------------------------------------
O QUE FAZ:
    Verificação das entradas da modelagem de isócronas (tempo de viagem
    pela malha viária, com caminho mínimo de Dijkstra sobre o grafo do
    OpenStreetMap):
      1) confirma a existência e informa o tamanho (MB) dos dois caches de
         extração do OpenStreetMap, um para a região das Cataratas e outro
         para a região de Bonito; se um deles não existir, a execução é
         interrompida com erro;
      2) lê a camada de portas rodoviárias federais e lista, para cada
         porta, o identificador, as rodovias, o município e as coordenadas
         que servem de origem na modelagem.
    Não grava arquivo; o resultado é impresso no terminal.

ENTRADAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/raw_osm_cataratas.json
    Entregas/Produto 4/raw_osm_bonito.json
        Caches de extração de vias do OpenStreetMap
        (https://www.openstreetmap.org), em JSON, gerados fora deste script.
    Entregas/Produto 4/produção/cruzamento_faixa_fronteira_rodovias_federais_pr_ms.geojson
        Campos usados: id (numérico), rodovias_str, municipio, lat, lon.

SAÍDAS:
    Somente impressão no terminal.

VARIÁVEIS DE AMBIENTE:
    P4_DADOS  (opcional) raiz da árvore de dados; padrão: `dados/` na raiz
              do repositório.

COMO EXECUTAR:
    python regional/04_modelagem_isocronas_acessibilidade/validar_entradas_geometrias_isocronas.py
================================================================================
"""

# ==============================================================================
# ETAPA 1: IMPORTAÇÃO DE PACOTES
# ==============================================================================

import os
import json
import math
import networkx as nx
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _caminhos import ENTREGAS

sys.stdout.reconfigure(encoding='utf-8')


# ==============================================================================
# ETAPA 2: CACHES DO OPENSTREETMAP
# ==============================================================================
prod_dir = str(ENTREGAS)
cache_cat = os.path.join(prod_dir, "raw_osm_cataratas.json")
cache_bon = os.path.join(prod_dir, "raw_osm_bonito.json")

print(f"Cache Cataratas existe: {os.path.exists(cache_cat)} ({os.path.getsize(cache_cat)/(1024*1024):.1f} MB)")
print(f"Cache Bonito existe: {os.path.exists(cache_bon)} ({os.path.getsize(cache_bon)/(1024*1024):.1f} MB)")

# ==============================================================================
# ETAPA 3: PORTAS FEDERAIS COMO ORIGENS
# ==============================================================================
p_fed_gates = os.path.join(prod_dir, "produção", "cruzamento_faixa_fronteira_rodovias_federais_pr_ms.geojson")
gdf_fed = gpd.read_file(p_fed_gates)
print(f"\nCarregadas {len(gdf_fed)} portas federais como origens simultâneas:")
for idx, r in gdf_fed.iterrows():
    print(f"P{r['id']:02d}: {r['rodovias_str']} ({r['municipio']}) -> ({r['lat']:.4f}, {r['lon']:.4f})")
