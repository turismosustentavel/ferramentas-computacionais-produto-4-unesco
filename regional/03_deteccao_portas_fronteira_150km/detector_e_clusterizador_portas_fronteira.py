# -*- coding: utf-8 -*-
"""
================================================================================
PROJETO UNESCO UNES 2369/2025 | ITAIPU PARQUETEC - TS.DTUR
PRODUTO 4: DIAGNÓSTICO REGIONAL DE INFRAESTRUTURA, MOBILIDADE E CONECTIVIDADE
================================================================================
MÓDULO 03: PORTAS DE ENTRADA NA FAIXA DE FRONTEIRA (150 KM)
SCRIPT: detector_e_clusterizador_portas_fronteira.py
--------------------------------------------------------------------------------
O QUE FAZ:
    Grava as camadas de portas de entrada rodoviárias nas pastas de produção:
      1) Portas federais: lista `portas_federais`, escrita no script
         (identificadores PR-01 a PR-09 e MS-01 a MS-09; rodovia, UF,
         município, tipo de porta, país ou região de destino, tipo de pista
         e coordenadas). A lista é convertida em pontos (EPSG:4326),
         gravada em GeoJSON e, reprojetada para SIRGAS 2000 (EPSG:4674),
         em Shapefile.
      2) Portas estaduais: lê a camada existente em Shapefile na pasta 14
         (ou, se ela não existir, o GeoJSON da pasta 12) e regrava as duas
         versões: GeoJSON no sistema da camada lida e Shapefile em SIRGAS
         2000. A identificação das portas estaduais é anterior a este
         script; aqui a camada apenas é padronizada.

ENTRADAS (caminhos relativos a P4_DADOS):
    Portas federais: coordenadas e atributos escritos no script.
    Portas estaduais (uma das duas):
        Entregas/Produto 4/produção/14_portas_estaduais_30_pontos_shp/14_portas_estaduais_30_pontos_shp.shp
        Entregas/Produto 4/produção/12_portas_entrada_terrestres_oficiais_shp/cruzamento_faixa_fronteira_rodovias_estaduais_pr_ms.geojson

SAÍDAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/12_portas_entrada_terrestres_oficiais_shp/
        cruzamento_faixa_fronteira_rodovias_federais_pr_ms.geojson    (EPSG:4326)
        cruzamento_faixa_fronteira_rodovias_estaduais_pr_ms.geojson
    Entregas/Produto 4/produção/13_portas_federais_18_pontos_shp/
        13_portas_federais_18_pontos_shp.shp                          (EPSG:4674)
    Entregas/Produto 4/produção/14_portas_estaduais_30_pontos_shp/
        14_portas_estaduais_30_pontos_shp.shp                         (EPSG:4674)

VARIÁVEIS DE AMBIENTE:
    P4_DADOS  (opcional) raiz da árvore de dados; padrão: `dados/` na raiz
              do repositório.

COMO EXECUTAR:
    python regional/03_deteccao_portas_fronteira_150km/detector_e_clusterizador_portas_fronteira.py
    python regional/03_deteccao_portas_fronteira_150km/detector_e_clusterizador_portas_fronteira.py --tipo federais
        --tipo  federais | estaduais | todas (padrão: todas)
================================================================================
"""

import os
import sys
import argparse
from pathlib import Path
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _caminhos import PRODUCAO

sys.stdout.reconfigure(encoding='utf-8')

prod_dir = str(PRODUCAO)
folder_12 = os.path.join(prod_dir, "12_portas_entrada_terrestres_oficiais_shp")
folder_13 = os.path.join(prod_dir, "13_portas_federais_18_pontos_shp")
folder_14 = os.path.join(prod_dir, "14_portas_estaduais_30_pontos_shp")
os.makedirs(folder_12, exist_ok=True)
os.makedirs(folder_13, exist_ok=True)
os.makedirs(folder_14, exist_ok=True)

# 1. Portas federais (coordenadas em graus, WGS 84)
portas_federais = [
    {"id": "MS-01", "rodovia": "BR-262", "uf": "MS", "municipio": "Corumbá", "tipo_porta": "Fronteira Internacional", "pais_destino": "Bolívia (Puerto Quijarro)", "tipo_pista": "Pavimentada Simples", "lat": -19.0284, "lon": -57.7081},
    {"id": "MS-02", "rodovia": "BR-262", "uf": "MS", "municipio": "Miranda", "tipo_porta": "Transição Faixa de Fronteira (150 km)", "pais_destino": "Brasil (Transição Interna MS)", "tipo_pista": "Pavimentada Simples", "lat": -20.1948, "lon": -56.4445},
    {"id": "MS-03", "rodovia": "BR-267", "uf": "MS", "municipio": "Porto Murtinho", "tipo_porta": "Fronteira Internacional", "pais_destino": "Paraguai (Carmelo Peralta)", "tipo_pista": "Pavimentada Simples", "lat": -21.6989, "lon": -57.8814},
    {"id": "MS-04", "rodovia": "BR-267", "uf": "MS", "municipio": "Guia Lopes da Laguna", "tipo_porta": "Transição Faixa de Fronteira (150 km)", "pais_destino": "Brasil (Transição Interna MS)", "tipo_pista": "Pavimentada Simples", "lat": -21.4645, "lon": -56.1284},
    {"id": "MS-05", "rodovia": "BR-463", "uf": "MS", "municipio": "Ponta Porã", "tipo_porta": "Fronteira Internacional", "pais_destino": "Paraguai (Pedro Juan Caballero)", "tipo_pista": "Pavimentada Simples", "lat": -22.5489, "lon": -55.7275},
    {"id": "MS-06", "rodovia": "BR-463", "uf": "MS", "municipio": "Dourados", "tipo_porta": "Transição Faixa de Fronteira (150 km)", "pais_destino": "Brasil (Transição Interna MS)", "tipo_pista": "Pavimentada Simples", "lat": -22.2514, "lon": -54.8514},
    {"id": "MS-07", "rodovia": "BR-163", "uf": "MS", "municipio": "Dourados", "tipo_porta": "Transição Faixa de Fronteira (150 km)", "pais_destino": "Brasil (Transição Interna MS)", "tipo_pista": "Pavimentada Dupla/Simples", "lat": -22.1845, "lon": -54.7814},
    {"id": "MS-08", "rodovia": "BR-163", "uf": "MS", "municipio": "Mundo Novo", "tipo_porta": "Transição Interestadual / Fronteira", "pais_destino": "Brasil (Divisa MS/PR) / Salto del Guairá", "tipo_pista": "Pavimentada Simples", "lat": -23.9489, "lon": -54.2814},
    {"id": "MS-09", "rodovia": "BR-376", "uf": "MS", "municipio": "Ivinhema", "tipo_porta": "Transição Faixa de Fronteira (150 km)", "pais_destino": "Brasil (Transição Interna MS)", "tipo_pista": "Pavimentada Simples", "lat": -22.3145, "lon": -53.8214},
    {"id": "PR-01", "rodovia": "BR-163", "uf": "PR", "municipio": "Guaíra", "tipo_porta": "Transição Interestadual (Ponte Ayrton Senna)", "pais_destino": "Brasil (Divisa PR/MS)", "tipo_pista": "Pavimentada Simples", "lat": -24.0814, "lon": -54.2584},
    {"id": "PR-02", "rodovia": "BR-272", "uf": "PR", "municipio": "Guaíra", "tipo_porta": "Transição Faixa de Fronteira (150 km)", "pais_destino": "Brasil (Transição Interna PR)", "tipo_pista": "Pavimentada Simples", "lat": -24.1514, "lon": -53.9814},
    {"id": "PR-03", "rodovia": "BR-369", "uf": "PR", "municipio": "Cascavel", "tipo_porta": "Transição Faixa de Fronteira (150 km)", "pais_destino": "Brasil (Transição Interna PR)", "tipo_pista": "Pavimentada Dupla", "lat": -24.8814, "lon": -53.3814},
    {"id": "PR-04", "rodovia": "BR-277", "uf": "PR", "municipio": "Cascavel", "tipo_porta": "Transição Faixa de Fronteira (150 km)", "pais_destino": "Brasil (Transição Interna PR)", "tipo_pista": "Pavimentada Dupla", "lat": -25.0214, "lon": -53.3514},
    {"id": "PR-05", "rodovia": "BR-277", "uf": "PR", "municipio": "Foz do Iguaçu", "tipo_porta": "Fronteira Internacional (Ponte da Amizade)", "pais_destino": "Paraguai (Ciudad del Este)", "tipo_pista": "Pavimentada Dupla", "lat": -25.5114, "lon": -54.6014},
    {"id": "PR-06", "rodovia": "BR-469", "uf": "PR", "municipio": "Foz do Iguaçu", "tipo_porta": "Fronteira Internacional (Ponte Tancredo Neves)", "pais_destino": "Argentina (Puerto Iguazú)", "tipo_pista": "Pavimentada Dupla", "lat": -25.5898, "lon": -54.5814},
    {"id": "PR-07", "rodovia": "BR-163", "uf": "PR", "municipio": "Capitão Leônidas Marques", "tipo_porta": "Transição Faixa de Fronteira (150 km)", "pais_destino": "Brasil (Transição Interna PR)", "tipo_pista": "Pavimentada Simples", "lat": -25.4814, "lon": -53.6114},
    {"id": "PR-08", "rodovia": "BR-280", "uf": "PR", "municipio": "Marmeleiro", "tipo_porta": "Transição Faixa de Fronteira (150 km)", "pais_destino": "Brasil (Transição Interna PR/SC)", "tipo_pista": "Pavimentada Simples", "lat": -26.1514, "lon": -53.0214},
    {"id": "PR-09", "rodovia": "BR-163", "uf": "PR", "municipio": "Barracão", "tipo_porta": "Fronteira Internacional", "pais_destino": "Argentina (Bernardo de Irigoyen)", "tipo_pista": "Pavimentada Simples", "lat": -26.2514, "lon": -53.6314}
]

def exportar_portas_federais():
    print("\n[1/2] Processando e exportando as 18 Portas Rodoviárias Federais...")
    df_fed = pd.DataFrame(portas_federais)
    gdf_fed = gpd.GeoDataFrame(df_fed, geometry=[Point(xy) for xy in zip(df_fed.lon, df_fed.lat)], crs="EPSG:4326")
    
    # GeoJSON em WGS 84 e Shapefile em SIRGAS 2000
    geojson_out = os.path.join(folder_12, "cruzamento_faixa_fronteira_rodovias_federais_pr_ms.geojson")
    gdf_fed.to_file(geojson_out, driver="GeoJSON")
    
    gdf_fed_sirgas = gdf_fed.to_crs(epsg=4674)
    shp_out = os.path.join(folder_13, "13_portas_federais_18_pontos_shp.shp")
    gdf_fed_sirgas.to_file(shp_out)
    print(f" [OK] 18 Portas Federais salvas em GeoJSON ({geojson_out}) e Shapefile ({shp_out})")

def exportar_portas_estaduais():
    print("\n[2/2] Processando e exportando as 30 Portas Rodoviárias Estaduais...")
    # Leitura da camada existente: Shapefile da pasta 14 ou, na falta dele,
    # GeoJSON da pasta 12
    src_est = os.path.join(folder_14, "14_portas_estaduais_30_pontos_shp.shp")
    if os.path.exists(src_est):
        gdf_est = gpd.read_file(src_est)
    else:
        src_geo = os.path.join(folder_12, "cruzamento_faixa_fronteira_rodovias_estaduais_pr_ms.geojson")
        gdf_est = gpd.read_file(src_geo)
        
    geojson_out = os.path.join(folder_12, "cruzamento_faixa_fronteira_rodovias_estaduais_pr_ms.geojson")
    gdf_est.to_file(geojson_out, driver="GeoJSON")
    shp_out = os.path.join(folder_14, "14_portas_estaduais_30_pontos_shp.shp")
    gdf_est.to_crs(epsg=4674).to_file(shp_out)
    print(f" [OK] 30 Portas Estaduais salvas em GeoJSON ({geojson_out}) e Shapefile ({shp_out})")

def main():
    parser = argparse.ArgumentParser(description="Detector e Consolidador de Portas de Fronteira")
    parser.add_argument('--tipo', choices=['federais', 'estaduais', 'todas'], default='todas')
    args = parser.parse_args()
    
    if args.tipo in ['federais', 'todas']:
        exportar_portas_federais()
    if args.tipo in ['estaduais', 'todas']:
        exportar_portas_estaduais()
        
    print("\n Consolidação das Portas de Fronteira executada com sucesso!")

if __name__ == '__main__':
    main()
