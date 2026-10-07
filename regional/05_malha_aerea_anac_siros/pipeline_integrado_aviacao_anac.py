# -*- coding: utf-8 -*-
"""
================================================================================
PROJETO UNESCO UNES 2369/2025 | ITAIPU PARQUETEC - TS.DTUR
PRODUTO 4: DIAGNÓSTICO REGIONAL DE INFRAESTRUTURA, MOBILIDADE E CONECTIVIDADE
================================================================================
MÓDULO 05: CONECTIVIDADE AÉREA REGIONAL (ANAC / SIROS)
SCRIPT: pipeline_integrado_aviacao_anac.py
--------------------------------------------------------------------------------
O QUE FAZ:
    Lê a camada de rotas aéreas regulares com destino aos aeroportos da
    Faixa de Fronteira (uma linha por rota origem-destino e companhia) e
    resume a movimentação por aeroporto de destino (código ICAO):
        total_pax     soma de passageiros pagos (pax_pag);
        rotas_ativas  número de registros de rota com destino ao aeroporto;
        cias          companhias aéreas que operam as rotas, em ordem
                      alfabética, sem repetição.
    Acrescenta o nome do aeroporto (dicionário `dest_airports`, escrito no
    script; código sem correspondência mantém o próprio ICAO), ordena por
    total de passageiros, imprime o resumo e grava a tabela.

ENTRADAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/09_aviacao_rotas_e_aeroportos_anac/
        malha_rotas_aereas_regulares_anac.shp
        Campos usados: dest_icao, orig_icao, pax_pag, cia_aerea.
        Fonte: Agência Nacional de Aviação Civil (ANAC), dados de voos
        regulares e de passageiros pagos (SIROS / Dados Estatísticos do
        Transporte Aéreo), preparados como camada de linhas fora deste
        script. Portal de dados e estatísticas da ANAC:
        https://www.gov.br/anac/pt-br/assuntos/dados-e-estatisticas

SAÍDAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/09_aviacao_rotas_e_aeroportos_anac/
        tabela_resumo_movimentacao_aeroportos_anac.csv
        Colunas: dest_icao, total_pax, rotas_ativas, cias, aeroporto.

VARIÁVEIS DE AMBIENTE:
    P4_DADOS  (opcional) raiz da árvore de dados; padrão: `dados/` na raiz
              do repositório.

COMO EXECUTAR:
    python regional/05_malha_aerea_anac_siros/pipeline_integrado_aviacao_anac.py
================================================================================
"""

# ==============================================================================
# ETAPA 1: IMPORTAÇÃO DE PACOTES
# ==============================================================================
import os
import sys
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _caminhos import PRODUCAO

sys.stdout.reconfigure(encoding='utf-8')

# ==============================================================================
# ETAPA 2: DIRETÓRIOS E CADASTRO DE AEROPORTOS
# ==============================================================================
prod_dir = str(PRODUCAO)
air_folder = os.path.join(prod_dir, "09_aviacao_rotas_e_aeroportos_anac")
p_air = os.path.join(air_folder, "malha_rotas_aereas_regulares_anac.shp")

# Aeroportos de destino na Faixa de Fronteira (código ICAO). Apenas o campo
# 'name' entra na tabela de saída; os demais são metadados de referência.
dest_airports = {
    'SBFI': {'name': 'Foz do Iguaçu (IGU)', 'city': 'Foz do Iguaçu', 'lat': -25.5960, 'lon': -54.4872, 'offset': (12, -18)},
    'SBCG': {'name': 'Campo Grande (CGR)', 'city': 'Campo Grande', 'lat': -20.4686, 'lon': -54.6725, 'offset': (12, 10)},
    'SBDB': {'name': 'Bonito (BYO)', 'city': 'Bonito', 'lat': -21.2464, 'lon': -56.4528, 'offset': (12, 8)},
    'SBCR': {'name': 'Corumbá (CMG)', 'city': 'Corumbá', 'lat': -19.0119, 'lon': -57.6714, 'offset': (12, 8)},
    'SBPP': {'name': 'Ponta Porã (PMG)', 'city': 'Ponta Porã', 'lat': -22.5497, 'lon': -55.7031, 'offset': (-140, -18)},
    'SSGY': {'name': 'Guaíra (GGY)', 'city': 'Guaíra', 'lat': -24.0647, 'lon': -54.2008, 'offset': (12, 8)}
}

# ==============================================================================
# ETAPA 3: RESUMO POR AEROPORTO DE DESTINO
# ==============================================================================
def processar_estatisticas_aviacao():
    print("\n[1/1] Processando microdados e estatísticas de voos regulares da ANAC...")
    gdf_air = gpd.read_file(p_air)

    # Agrupamento por aeroporto de destino
    resumo_destinos = gdf_air.groupby('dest_icao').agg(
        total_pax=('pax_pag', 'sum'),
        rotas_ativas=('orig_icao', 'count'),
        cias=('cia_aerea', lambda x: ", ".join(sorted(set(x))))
    ).reset_index()

    resumo_destinos['aeroporto'] = resumo_destinos['dest_icao'].map(lambda x: dest_airports.get(x, {}).get('name', x))
    resumo_destinos = resumo_destinos.sort_values(by='total_pax', ascending=False)

    print("\n--- RESUMO DE MOVIMENTAÇÃO DE PASSAGEIROS RECEBIDOS (SIROS/ANAC) ---")
    print(resumo_destinos[['aeroporto', 'total_pax', 'rotas_ativas', 'cias']].to_string(index=False))

    # Gravação da tabela
    csv_resumo = os.path.join(air_folder, "tabela_resumo_movimentacao_aeroportos_anac.csv")
    resumo_destinos.to_csv(csv_resumo, index=False, encoding='utf-8')
    print(f"\n Tabela resumo salva em: {csv_resumo}")
    return gdf_air

# ==============================================================================
# ETAPA 4: EXECUÇÃO PRINCIPAL
# ==============================================================================
def main():
    gdf_air = processar_estatisticas_aviacao()
    print("\n Pipeline de Aviação Comercial concluído com êxito!")

if __name__ == '__main__':
    main()
