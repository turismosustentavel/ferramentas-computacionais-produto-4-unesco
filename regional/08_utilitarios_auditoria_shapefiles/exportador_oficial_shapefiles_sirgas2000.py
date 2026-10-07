# -*- coding: utf-8 -*-
"""
================================================================================
PROJETO UNESCO UNES 2369/2025 | ITAIPU PARQUETEC - TS.DTUR
PRODUTO 4: DIAGNÓSTICO REGIONAL DE INFRAESTRUTURA, MOBILIDADE E CONECTIVIDADE
================================================================================
MÓDULO 08: UTILITÁRIOS DE AUDITORIA DE DADOS E SHAPEFILES
SCRIPT: exportador_oficial_shapefiles_sirgas2000.py
--------------------------------------------------------------------------------
O QUE FAZ:
    Converte a camada consolidada de portas de entrada terrestres de GeoJSON
    para Shapefile:
      1) mantém apenas as colunas essenciais presentes na camada e as
         renomeia para nomes de até 10 caracteres (limite do formato DBF):
             jurisdicao_principal -> jurisdicao   rodovia_principal -> rod_princ
             administracao        -> admin        local_inicio      -> loc_inicio
             local_fim            -> loc_fim      lat               -> latitude
             lon                  -> longitude    rodovias_str      -> rodovias
             (num_porta, uf e superficie mantêm o nome);
      2) grava duas versões: SIRGAS 2000 (EPSG:4674, referência oficial do
         Brasil) e WGS 84 (EPSG:4326);
      3) grava os arquivos .cpg com a codificação UTF-8.

ENTRADAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/portas_de_entrada_terrestres_faixa_fronteira.geojson
        Camada consolidada de portas de entrada (pontos), preparada fora
        deste script.

SAÍDAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/12_portas_entrada_terrestres_oficiais_shp/
        portas_de_entrada_terrestres_SIRGAS2000.shp (+ .dbf, .shx, .prj, .cpg)
        portas_de_entrada_terrestres_WGS84.shp      (+ .dbf, .shx, .prj, .cpg)

VARIÁVEIS DE AMBIENTE:
    P4_DADOS  (opcional) raiz da árvore de dados; padrão: `dados/` na raiz
              do repositório.

COMO EXECUTAR:
    python regional/08_utilitarios_auditoria_shapefiles/exportador_oficial_shapefiles_sirgas2000.py
================================================================================
"""

# ==============================================================================
# ETAPA 1: IMPORTAÇÃO DE PACOTES
# ==============================================================================

import os
import sys
from pathlib import Path
import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _caminhos import PRODUCAO

out_dir = str(PRODUCAO)
p_geojson = os.path.join(out_dir, "portas_de_entrada_terrestres_faixa_fronteira.geojson")

gdf_portas = gpd.read_file(p_geojson)
print("Colunas originais:", gdf_portas.columns.tolist())

# Selecionar e renomear apenas colunas essenciais sem duplicidade
cols = {
    'num_porta': 'num_porta',
    'jurisdicao_principal': 'jurisdicao',
    'rodovia_principal': 'rod_princ',
    'uf': 'uf',
    'superficie': 'superficie',
    'administracao': 'admin',
    'local_inicio': 'loc_inicio',
    'local_fim': 'loc_fim',
    'lat': 'latitude',
    'lon': 'longitude',
    'rodovias_str': 'rodovias',
    'geometry': 'geometry'
}

gdf_clean = gdf_portas[[c for c in cols.keys() if c in gdf_portas.columns]].copy()
gdf_clean = gdf_clean.rename(columns={k: v for k, v in cols.items() if k != 'geometry'})

print("Colunas ajustadas:", gdf_clean.columns.tolist())

shp_dir = os.path.join(out_dir, "12_portas_entrada_terrestres_oficiais_shp")
os.makedirs(shp_dir, exist_ok=True)

# 1. SIRGAS 2000 (EPSG:4674, referência oficial do Brasil / IBGE)
gdf_sirgas = gdf_clean.to_crs(epsg=4674)
shp_path_sirgas = os.path.join(shp_dir, "portas_de_entrada_terrestres_SIRGAS2000.shp")
gdf_sirgas.to_file(shp_path_sirgas, encoding='utf-8')

# 2. WGS 84 (EPSG:4326)
gdf_wgs84 = gdf_clean.to_crs(epsg=4326)
shp_path_wgs84 = os.path.join(shp_dir, "portas_de_entrada_terrestres_WGS84.shp")
gdf_wgs84.to_file(shp_path_wgs84, encoding='utf-8')

# Arquivos .cpg com a codificação UTF-8
with open(os.path.join(shp_dir, "portas_de_entrada_terrestres_SIRGAS2000.cpg"), "w", encoding='utf-8') as f:
    f.write("UTF-8")
with open(os.path.join(shp_dir, "portas_de_entrada_terrestres_WGS84.cpg"), "w", encoding='utf-8') as f:
    f.write("UTF-8")

print("\nShapefiles gerados com sucesso!")
