# -*- coding: utf-8 -*-
"""
================================================================================
PROJETO UNESCO UNES 2369/2025 | ITAIPU PARQUETEC - TS.DTUR
PRODUTO 4: DIAGNÓSTICO REGIONAL DE INFRAESTRUTURA, MOBILIDADE E CONECTIVIDADE
================================================================================
MÓDULO 03: PORTAS DE ENTRADA NA FAIXA DE FRONTEIRA (150 KM)
SCRIPT: mapeador_aduanas_e_travessias_internacionais.py
--------------------------------------------------------------------------------
O QUE FAZ:
    Converte em camada de pontos (EPSG:4326) o cadastro de travessias
    internacionais rodoviárias entre o Paraná / Mato Grosso do Sul e os
    países vizinhos (pontes internacionais, aduanas, passagens de fronteira
    seca e travessia em obras), escrito no script na lista
    `aduanas_internacionais`: identificador, nome, UF, município, país e
    cidade vizinhos, tipo de travessia, situação e coordenadas.
    Grava a camada em GeoJSON e imprime o resumo no terminal.

ENTRADAS (caminhos relativos a P4_DADOS):
    Nenhum arquivo. Cadastro escrito no script, com base em informações da
    Receita Federal do Brasil (unidades aduaneiras), da Polícia Federal
    (postos de controle migratório) e de vistorias de campo.

SAÍDAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/12_portas_entrada_terrestres_oficiais_shp/
        travessias_internacionais_aduanas.geojson   (EPSG:4326)

VARIÁVEIS DE AMBIENTE:
    P4_DADOS  (opcional) raiz da árvore de dados; padrão: `dados/` na raiz
              do repositório.

COMO EXECUTAR:
    python regional/03_deteccao_portas_fronteira_150km/mapeador_aduanas_e_travessias_internacionais.py
================================================================================
"""

import os
import sys
from pathlib import Path
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _caminhos import PRODUCAO

sys.stdout.reconfigure(encoding='utf-8')

prod_dir = str(PRODUCAO)
out_dir = os.path.join(prod_dir, "12_portas_entrada_terrestres_oficiais_shp")
os.makedirs(out_dir, exist_ok=True)

# Travessias internacionais (coordenadas em graus, WGS 84)
aduanas_internacionais = [
    {"id": "INT-01", "nome": "Ponte Internacional da Amizade", "uf": "PR", "municipio": "Foz do Iguaçu", "pais_vizinho": "Paraguai", "cidade_vizinha": "Ciudad del Este", "tipo_travessia": "Ponte Internacional Rodoviária", "status": "Ativa", "lat": -25.5114, "lon": -54.6014},
    {"id": "INT-02", "nome": "Ponte Internacional Tancredo Neves (Fraternidade)", "uf": "PR", "municipio": "Foz do Iguaçu", "pais_vizinho": "Argentina", "cidade_vizinha": "Puerto Iguazú", "tipo_travessia": "Ponte Internacional Rodoviária", "status": "Ativa", "lat": -25.5898, "lon": -54.5814},
    {"id": "INT-03", "nome": "Aduana de Capanema (Porto Mauá)", "uf": "PR", "municipio": "Capanema", "pais_vizinho": "Argentina", "cidade_vizinha": "Comandante Andresito", "tipo_travessia": "Ponte sobre o Rio Santo Antônio", "status": "Ativa", "lat": -25.6814, "lon": -53.8814},
    {"id": "INT-04", "nome": "Aduana Integrada de Cargas e Turistas", "uf": "PR", "municipio": "Barracão / Dionísio Cerqueira", "pais_vizinho": "Argentina", "cidade_vizinha": "Bernardo de Irigoyen", "tipo_travessia": "Fronteira Seca Urbana", "status": "Ativa", "lat": -26.2514, "lon": -53.6314},
    {"id": "INT-05", "nome": "Aduana de Santo Antônio do Sudoeste", "uf": "PR", "municipio": "Santo Antônio do Sudoeste", "pais_vizinho": "Argentina", "cidade_vizinha": "San Antonio", "tipo_travessia": "Ponte Rodoviária", "status": "Ativa", "lat": -26.0714, "lon": -53.7214},
    {"id": "INT-06", "nome": "Ponte Bioceânica (Carmelo Peralta)", "uf": "MS", "municipio": "Porto Murtinho", "pais_vizinho": "Paraguai", "cidade_vizinha": "Carmelo Peralta", "tipo_travessia": "Ponte Internacional em Obras / Balsa", "status": "Em Conclusão", "lat": -21.6989, "lon": -57.8814},
    {"id": "INT-07", "nome": "Aduana de Bela Vista", "uf": "MS", "municipio": "Bela Vista", "pais_vizinho": "Paraguai", "cidade_vizinha": "Bella Vista Norte", "tipo_travessia": "Ponte sobre o Rio Apa", "status": "Ativa", "lat": -22.1114, "lon": -56.5214},
    {"id": "INT-08", "nome": "Aduana de Ponta Porã (Linha Internacional)", "uf": "MS", "municipio": "Ponta Porã", "pais_vizinho": "Paraguai", "cidade_vizinha": "Pedro Juan Caballero", "tipo_travessia": "Fronteira Seca Contínua (Avenida Internacional)", "status": "Ativa", "lat": -22.5489, "lon": -55.7275},
    {"id": "INT-09", "nome": "Aduana do Posto Esdras", "uf": "MS", "municipio": "Corumbá", "pais_vizinho": "Bolívia", "cidade_vizinha": "Puerto Quijarro", "tipo_travessia": "Passagem Terrestre Internacional", "status": "Ativa", "lat": -19.0284, "lon": -57.7081}
]

def mapear_aduanas():
    print("\n[1/1] Mapeando e exportando as travessias internacionais oficiais...")
    df = pd.DataFrame(aduanas_internacionais)
    gdf = gpd.GeoDataFrame(df, geometry=[Point(xy) for xy in zip(df.lon, df.lat)], crs="EPSG:4326")
    
    out_geojson = os.path.join(out_dir, "travessias_internacionais_aduanas.geojson")
    gdf.to_file(out_geojson, driver="GeoJSON")
    print(f" [OK] {len(gdf)} Travessias Internacionais salvas em: {out_geojson}")
    
    print("\n--- RESUMO DAS TRAVESSIAS INTERNACIONAIS DA FAIXA DE FRONTEIRA ---")
    print(df[['id', 'nome', 'municipio', 'pais_vizinho', 'tipo_travessia', 'status']].to_string(index=False))

if __name__ == '__main__':
    mapear_aduanas()
