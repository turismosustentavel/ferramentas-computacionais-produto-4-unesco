# -*- coding: utf-8 -*-
"""
================================================================================
PROJETO UNESCO UNES 2369/2025 | ITAIPU PARQUETEC - TS.DTUR
PRODUTO 4: DIAGNÓSTICO REGIONAL DE INFRAESTRUTURA, MOBILIDADE E CONECTIVIDADE
================================================================================
MÓDULO 03: PORTAS DE ENTRADA NA FAIXA DE FRONTEIRA (150 KM)
SCRIPT: auditor_unificado_geometrias_e_portas.py
--------------------------------------------------------------------------------
O QUE FAZ:
    Ferramenta de inspeção da malha federal do SNV, usada para conferir a
    posição das portas de entrada rodoviárias. Para a rodovia federal
    informada (por exemplo 163, 262, 463, 277):
      1) seleciona os trechos do SNV com Codigo_BR igual ao número informado;
      2) restringe aos trechos com Unidade_Fe em PR, MS ou SC;
      3) imprime, para até 15 trechos, a UF, os locais de início e fim, a
         caixa envolvente (latitude e longitude mínimas e máximas) e o tipo
         de superfície.
    Não grava arquivo; o resultado é impresso no terminal.

ENTRADAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/02_malha_rodoviaria_nacional_dnit_snv_shp/
        02_malha_rodoviaria_nacional_dnit_snv_shp.shp
        Campos usados: Codigo_BR, Unidade_Fe, Local_Inic, Local_Fim,
        Superficie.
        Fonte: Sistema Nacional de Viação (DNIT):
        https://www.gov.br/dnit/pt-br/assuntos/atlas-e-mapas/pnv-e-snv

SAÍDAS:
    Somente impressão no terminal.

VARIÁVEIS DE AMBIENTE:
    P4_DADOS  (opcional) raiz da árvore de dados; padrão: `dados/` na raiz
              do repositório.

COMO EXECUTAR:
    python regional/03_deteccao_portas_fronteira_150km/auditor_unificado_geometrias_e_portas.py --rodovia 163
        --rodovia  número da rodovia federal (padrão: 163)
================================================================================
"""

import os
import sys
import argparse
from pathlib import Path
import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _caminhos import PRODUCAO

sys.stdout.reconfigure(encoding='utf-8')

prod_dir = str(PRODUCAO)
p_snv = os.path.join(prod_dir, "02_malha_rodoviaria_nacional_dnit_snv_shp", "02_malha_rodoviaria_nacional_dnit_snv_shp.shp")

def auditar_rodovia(cod_br):
    """Imprime os trechos da BR informada no PR, MS e SC (até 15)."""
    print(f"\n================================================================================")
    print(f" AUDITANDO SEGMENTOS DA RODOVIA BR-{cod_br} NA FAIXA DE FRONTEIRA")
    print(f"================================================================================")
    if not os.path.exists(p_snv):
        print(f"Malha SNV não encontrada em: {p_snv}")
        return

    gdf_snv = gpd.read_file(p_snv)
    snv_sub = gdf_snv[gdf_snv['Codigo_BR'] == str(cod_br)]
    print(f"Total de trechos cadastrados no Brasil: {len(snv_sub)}")

    snv_study = snv_sub[snv_sub['Unidade_Fe'].isin(['PR', 'MS', 'SC'])]
    print(f"Total de trechos na área do estudo (PR/MS/SC): {len(snv_study)}")

    for idx, r in snv_study.head(15).iterrows():
        minx, miny, maxx, maxy = r.geometry.bounds
        print(f"  UF: {r['Unidade_Fe']} | Trecho: {r.get('Local_Inic', '')} -> {r.get('Local_Fim', '')} | Bounds: [{miny:.4f}, {minx:.4f}] a [{maxy:.4f}, {maxx:.4f}] | Sup: {r.get('Superficie', '')}")

def main():
    parser = argparse.ArgumentParser(description="Auditor Unificado de Geometrias e Portas de Fronteira")
    parser.add_argument('--rodovia', default='163', help="Número da rodovia federal a inspecionar (ex.: 163, 262, 463, 277)")
    args = parser.parse_args()

    auditar_rodovia(args.rodovia)

if __name__ == '__main__':
    main()
