# -*- coding: utf-8 -*-
"""
================================================================================
PROJETO UNESCO UNES 2369/2025 | ITAIPU PARQUETEC - TS.DTUR
PRODUTO 4: DIAGNÓSTICO REGIONAL DE INFRAESTRUTURA, MOBILIDADE E CONECTIVIDADE
================================================================================
MÓDULO 08: UTILITÁRIOS DE AUDITORIA DE DADOS E SHAPEFILES
SCRIPT: auditor_geral_integridade_e_pavimento.py
--------------------------------------------------------------------------------
O QUE FAZ:
    Duas verificações, com resultado impresso no terminal:
      1) Cadastro dos municípios do estudo: imprime a lista
         `municipios_estudo`, escrita no script (nome, UF, código IBGE de
         7 dígitos e polo turístico de referência), para conferência dos
         códigos.
      2) Pavimentação da malha rodoviária: lê a base de pavimentação do DNIT
         e conta os segmentos por tipo de superfície, usando o campo
         'Superficie' ou, na falta dele, 'revestimen'.
    Não grava arquivo.

ENTRADAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/03_malha_rodoviaria_pavimentacao_dnit_cide_shp/
        03_malha_rodoviaria_pavimentacao_dnit_cide_shp.shp
        Malha rodoviária com situação de pavimentação (DNIT, base CIDE).
        Página de atlas e mapas do DNIT:
        https://www.gov.br/dnit/pt-br/assuntos/atlas-e-mapas
    Códigos de município: códigos IBGE de 7 dígitos escritos no script,
    a conferir na API de localidades do IBGE
    (https://servicodados.ibge.gov.br/api/docs/localidades).

SAÍDAS:
    Somente impressão no terminal.

VARIÁVEIS DE AMBIENTE:
    P4_DADOS  (opcional) raiz da árvore de dados; padrão: `dados/` na raiz
              do repositório.

COMO EXECUTAR:
    python regional/08_utilitarios_auditoria_shapefiles/auditor_geral_integridade_e_pavimento.py
================================================================================
"""

import os
import sys
import argparse
from pathlib import Path
import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _caminhos import PRODUCAO

sys.stdout.reconfigure(encoding='utf-8')

prod_dir = str(PRODUCAO)
p_cide = os.path.join(prod_dir, "03_malha_rodoviaria_pavimentacao_dnit_cide_shp", "03_malha_rodoviaria_pavimentacao_dnit_cide_shp.shp")

# Municípios do estudo (nome, UF, código IBGE e polo de referência)
municipios_estudo = [
    {"nome": "Foz do Iguaçu", "uf": "PR", "cod_ibge": 4108304, "polo": "Polo Cataratas / Trinacional"},
    {"nome": "Santa Terezinha de Itaipu", "uf": "PR", "cod_ibge": 4124053, "polo": "Lindeiro Itaipu"},
    {"nome": "São Miguel do Iguaçu", "uf": "PR", "cod_ibge": 4125704, "polo": "Lindeiro Itaipu"},
    {"nome": "Medianeira", "uf": "PR", "cod_ibge": 4115804, "polo": "Corredor BR-277"},
    {"nome": "Santa Helena", "uf": "PR", "cod_ibge": 4123501, "polo": "Balneários do Lago"},
    {"nome": "Guaíra", "uf": "PR", "cod_ibge": 4108809, "polo": "Polo Ilha Grande / Conexão MS"},
    {"nome": "Barracão", "uf": "PR", "cod_ibge": 4102703, "polo": "Tríplice Fronteira Sul (PR/SC/ARG)"},
    {"nome": "Capanema", "uf": "PR", "cod_ibge": 4104501, "polo": "Parque Nacional do Iguaçu Sul"},
    {"nome": "Mundo Novo", "uf": "MS", "cod_ibge": 5005707, "polo": "Cone Sul / Salto del Guairá"},
    {"nome": "Ponta Porã", "uf": "MS", "cod_ibge": 5006606, "polo": "Fronteira Seca Pedro Juan"},
    {"nome": "Porto Murtinho", "uf": "MS", "cod_ibge": 5006903, "polo": "Portal Rota Bioceânica"},
    {"nome": "Corumbá", "uf": "MS", "cod_ibge": 5003207, "polo": "Pantanal / Fronteira Bolívia"}
]

def auditar_municipios():
    print("\n[1/2] AUDITORIA DOS 12 MUNICÍPIOS DO ESTUDO:")
    df_m = pd.DataFrame(municipios_estudo)
    print(df_m.to_string(index=False))

def auditar_pavimento():
    print("\n[2/2] AUDITORIA DA MALHA DE PAVIMENTAÇÃO (CIDE/DNIT):")
    if os.path.exists(p_cide):
        gdf = gpd.read_file(p_cide)
        print(f"Total de segmentos carregados: {len(gdf)}")
        col_sup = 'Superficie' if 'Superficie' in gdf.columns else 'revestimen' if 'revestimen' in gdf.columns else None
        if col_sup:
            resumo = gdf[col_sup].value_counts()
            print("\nDistribuição por Tipo de Superfície / Pavimento:")
            print(resumo.to_string())
    else:
        print(f"Base CIDE não encontrada em: {p_cide}")

def main():
    auditar_municipios()
    auditar_pavimento()
    print("\n[OK] Auditoria geral de integridade concluída!")

if __name__ == '__main__':
    main()
