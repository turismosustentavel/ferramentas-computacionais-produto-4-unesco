# -*- coding: utf-8 -*-
"""
================================================================================
PROJETO UNESCO UNES 2369/2025 | ITAIPU PARQUETEC - TS.DTUR
PRODUTO 4: DIAGNÓSTICO REGIONAL DE INFRAESTRUTURA, MOBILIDADE E CONECTIVIDADE
================================================================================
MÓDULO 03: PORTAS DE ENTRADA NA FAIXA DE FRONTEIRA (150 KM)
SCRIPT: mapeador_acessos_vicinais_e_rotas_informais_osm.py
--------------------------------------------------------------------------------
O QUE FAZ:
    Lê a camada de pontos em que vias vicinais do OpenStreetMap (estradas
    rurais, de terra, cascalho ou leito natural) cruzam o limite da Faixa
    de Fronteira de 150 km ou a fronteira internacional, reprojeta-a para
    SIRGAS 2000 (EPSG:4674) e grava em Shapefile. A extração dos
    cruzamentos é anterior a este script; aqui a camada é convertida e
    padronizada.

ENTRADAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/12_portas_entrada_terrestres_oficiais_shp/
        cruzamento_faixa_fronteira_estradas_vicinais_osm.geojson
    Se o arquivo não estiver nessa pasta, é procurado na raiz de
    Entregas/Produto 4/produção/.
    Fonte das vias: OpenStreetMap (https://www.openstreetmap.org), vias
    classificadas como highway=unclassified ou highway=track.

SAÍDAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/15_portas_vicinais_nao_pavimentadas_osm_shp/
        15_portas_vicinais_nao_pavimentadas_osm_shp.shp   (EPSG:4674)

VARIÁVEIS DE AMBIENTE:
    P4_DADOS  (opcional) raiz da árvore de dados; padrão: `dados/` na raiz
              do repositório.

COMO EXECUTAR:
    python regional/03_deteccao_portas_fronteira_150km/mapeador_acessos_vicinais_e_rotas_informais_osm.py
================================================================================
"""

import os
import sys
from pathlib import Path
import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _caminhos import PRODUCAO

sys.stdout.reconfigure(encoding='utf-8')

prod_dir = str(PRODUCAO)
folder_12 = os.path.join(prod_dir, "12_portas_entrada_terrestres_oficiais_shp")
folder_15 = os.path.join(prod_dir, "15_portas_vicinais_nao_pavimentadas_osm_shp")
os.makedirs(folder_15, exist_ok=True)

def processar_vicinais():
    print("\n[1/1] Processando e exportando as portas e acessos vicinais não pavimentados (OSM)...")
    src_geo = os.path.join(folder_12, "cruzamento_faixa_fronteira_estradas_vicinais_osm.geojson")
    if not os.path.exists(src_geo):
        alt = os.path.join(prod_dir, "cruzamento_faixa_fronteira_estradas_vicinais_osm.geojson")
        if os.path.exists(alt):
            src_geo = alt
        else:
            print(f"Arquivo de entrada não encontrado: {src_geo}")
            return

    gdf = gpd.read_file(src_geo)
    print(f"Total de pontos vicinais carregados: {len(gdf)}")

    # Shapefile em SIRGAS 2000
    shp_out = os.path.join(folder_15, "15_portas_vicinais_nao_pavimentadas_osm_shp.shp")
    gdf_sirgas = gdf.to_crs(epsg=4674)
    gdf_sirgas.to_file(shp_out)
    print(f" [OK] Camada de acessos vicinais salva com sucesso em: {shp_out}")

if __name__ == '__main__':
    processar_vicinais()
