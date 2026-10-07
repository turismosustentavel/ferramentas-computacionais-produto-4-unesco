# -*- coding: utf-8 -*-
"""
================================================================================
PROJETO UNESCO UNES 2369/2025 | ITAIPU PARQUETEC - TS.DTUR
PRODUTO 4: DIAGNÓSTICO REGIONAL DE INFRAESTRUTURA, MOBILIDADE E CONECTIVIDADE
================================================================================
MÓDULO 02: MONITORAMENTO DE TRÁFEGO (TOMTOM API)
SCRIPT: medidor_velocidades_reais_tomtom.py
--------------------------------------------------------------------------------
O QUE FAZ:
    Consulta a TomTom Traffic API (Flow Segment Data, versão 4, estilo
    "absolute", zoom 10, unidade km/h) no ponto de cada porta de entrada e
    registra, para o segmento viário mais próximo do ponto, a velocidade
    atual e a velocidade de fluxo livre informadas pela API no momento da
    execução. Três conjuntos de portas: federais, estaduais e vicinais.

    Para cada porta:
        velocidade_real_kmh   = currentSpeed
        velocidade_livre_kmh  = freeFlowSpeed (se ausente: max(currentSpeed, 60))
        confianca             = confidence (se ausente: 1,0)
        razao_fluidez         = velocidade_real / velocidade_livre
                                (1,0 se a velocidade livre for zero)
        perda_pct             = max(0, (1 - razao_fluidez) x 100)
        status_fluxo:
            razao < 0,70          Intenso / Retenção Severa
            0,70 <= razao < 0,88  Moderado / Alerta de Fluidez
            razao >= 0,88         Fluidez Plena / Tráfego Livre
        cor_badge: código de cor associado ao status.

    Quando a API não responde ou devolve resposta vazia, a porta é gravada
    com valores estimados: 60 km/h real e livre, razão 1,0, perda 0,
    status "Fluidez Plena (Estimada)" e confiança 0,5.
    Há pausa de 0,15 s entre consultas. As requisições HTTPS usam contexto
    SSL sem verificação de certificado.

ENTRADAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/12_portas_entrada_terrestres_oficiais_shp/
        cruzamento_faixa_fronteira_rodovias_federais_pr_ms.geojson
        cruzamento_faixa_fronteira_rodovias_estaduais_pr_ms.geojson
        cruzamento_faixa_fronteira_estradas_vicinais_osm.geojson
    Se um arquivo não estiver nessa pasta, é procurado na raiz de
    Entregas/Produto 4/produção/.
    Campos usados: id; rodovias_str (federais e estaduais) ou name
    (vicinais); municipio; uf; geometria de ponto (ou lat/lon).
    Fonte dos dados de tráfego: TomTom Traffic API, Flow Segment Data
    (https://docs.tomtom.com/traffic-api/documentation/tomtom-maps/traffic-flow/flow-segment-data).

SAÍDAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/05_telemetria_velocidades_reais_tomtom/
        fluxo_tomtom_portas_federais_faixa_5km.csv
        fluxo_tomtom_portas_estaduais_faixa_5km.csv
        fluxo_tomtom_estradas_vicinais_faixa_5km.csv
    Colunas: id, rodovia, uf, municipio, lat, lon, velocidade_real_kmh,
    velocidade_livre_kmh, razao_fluidez, perda_pct, status_fluxo,
    cor_badge, confianca.

VARIÁVEIS DE AMBIENTE:
    TOMTOM_API_KEY  (obrigatória) chave da TomTom Traffic API.
    P4_DADOS        (opcional) raiz da árvore de dados; padrão: `dados/`
                    na raiz do repositório.

COMO EXECUTAR:
    python regional/02_monitoramento_trafego_tomtom/medidor_velocidades_reais_tomtom.py
    python regional/02_monitoramento_trafego_tomtom/medidor_velocidades_reais_tomtom.py --tipo federais
    python regional/02_monitoramento_trafego_tomtom/medidor_velocidades_reais_tomtom.py --testar
        --tipo    federais | estaduais | vicinais | todas (padrão: todas)
        --testar  apenas testa a conexão e a chave com um ponto em Foz do Iguaçu
    Os valores dependem do instante da consulta: execuções em horários
    diferentes produzem velocidades diferentes.
================================================================================
"""

# ==============================================================================
# ETAPA 1: IMPORTAÇÃO DE PACOTES
# ==============================================================================
import os
import sys
import json
import urllib.request
import ssl
import time
import argparse
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _caminhos import PRODUCAO

sys.stdout.reconfigure(encoding='utf-8')

# ==============================================================================
# ETAPA 2: DIRETÓRIOS E CREDENCIAL
# ==============================================================================
prod_dir = str(PRODUCAO)
out_csv_dir = os.path.join(prod_dir, "05_telemetria_velocidades_reais_tomtom")
os.makedirs(out_csv_dir, exist_ok=True)

# Chave da TomTom Traffic API, lida da variável de ambiente TOMTOM_API_KEY.
try:
    tomtom_key = os.environ["TOMTOM_API_KEY"]
except KeyError:
    sys.exit(
        "Variável de ambiente TOMTOM_API_KEY não definida.\n"
        "Defina-a com a chave da TomTom Traffic API antes de executar, por exemplo:\n"
        "  PowerShell:  $env:TOMTOM_API_KEY = \"<sua chave>\"\n"
        "  bash:        export TOMTOM_API_KEY=\"<sua chave>\""
    )

# Contexto SSL sem verificação de certificado.
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ==============================================================================
# ETAPA 3: FUNÇÕES DE CONSULTA À API DA TOMTOM
# ==============================================================================
def testar_conexao():
    """Consulta um ponto em Foz do Iguaçu para validar a conexão e a chave."""
    print("\n[TESTE] Verificando conexão e chave de API com a TomTom...")
    lat, lon = -25.5158, -54.5854 # Foz do Iguaçu
    url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?point={lat},{lon}&unit=KMPH&key={tomtom_key}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            flow = data.get('flowSegmentData', {})
            print(f" Conexão estabelecida com sucesso!")
            print(f"   Velocidade Atual: {flow.get('currentSpeed', 0)} km/h | Fluxo Livre: {flow.get('freeFlowSpeed', 0)} km/h")
            return True
    except Exception as e:
        print(f" Erro ao conectar com a TomTom API: {e}")
        return False

def get_tomtom_flow(lat, lon):
    """Devolve o bloco 'flowSegmentData' da resposta, ou None em caso de erro."""
    url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?point={lat},{lon}&unit=KMPH&key={tomtom_key}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('flowSegmentData', {})
    except Exception as e:
        return None

# ==============================================================================
# ETAPA 4: PROCESSAMENTO POR TIPO DE PORTA
# ==============================================================================
def processar_portas(tipo='federais'):
    config = {
        'federais': {
            'nome': 'Portas Rodoviárias Federais',
            'geojson': os.path.join(prod_dir, "12_portas_entrada_terrestres_oficiais_shp", "cruzamento_faixa_fronteira_rodovias_federais_pr_ms.geojson"),
            'csv_out': os.path.join(out_csv_dir, "fluxo_tomtom_portas_federais_faixa_5km.csv"),
            'id_col': 'id', 'rod_col': 'rodovias_str', 'muni_col': 'municipio'
        },
        'estaduais': {
            'nome': 'Portas Rodoviárias Estaduais',
            'geojson': os.path.join(prod_dir, "12_portas_entrada_terrestres_oficiais_shp", "cruzamento_faixa_fronteira_rodovias_estaduais_pr_ms.geojson"),
            'csv_out': os.path.join(out_csv_dir, "fluxo_tomtom_portas_estaduais_faixa_5km.csv"),
            'id_col': 'id', 'rod_col': 'rodovias_str', 'muni_col': 'municipio'
        },
        'vicinais': {
            'nome': 'Acessos Vicinais Não Pavimentados (OSM)',
            'geojson': os.path.join(prod_dir, "12_portas_entrada_terrestres_oficiais_shp", "cruzamento_faixa_fronteira_estradas_vicinais_osm.geojson"),
            'csv_out': os.path.join(out_csv_dir, "fluxo_tomtom_estradas_vicinais_faixa_5km.csv"),
            'id_col': 'id', 'rod_col': 'name', 'muni_col': 'municipio'
        }
    }

    cfg = config.get(tipo)
    if not cfg:
        print(f"Tipo '{tipo}' não reconhecido. Use: federais, estaduais ou vicinais.")
        return

    print(f"\n================================================================================")
    print(f" INICIANDO PROCESSAMENTO: {cfg['nome'].upper()}")
    print(f"================================================================================")

    if not os.path.exists(cfg['geojson']):
        # Caminho alternativo: o mesmo arquivo na raiz da pasta de produção
        alt = os.path.join(prod_dir, os.path.basename(cfg['geojson']))
        if os.path.exists(alt):
            cfg['geojson'] = alt
        else:
            print(f"Arquivo de entrada GeoJSON não encontrado: {cfg['geojson']}")
            return

    gdf = gpd.read_file(cfg['geojson'])
    print(f"Registros carregados: {len(gdf)}")

    results = []
    for idx, r in gdf.iterrows():
        p_id = r.get(cfg['id_col'], idx + 1)
        p_rod = str(r.get(cfg['rod_col'], 'Via Local'))
        p_muni = str(r.get(cfg['muni_col'], 'Fronteira'))
        p_uf = str(r.get('uf', 'PR/MS'))
        p_lat = r.geometry.y if hasattr(r, 'geometry') and r.geometry else r.get('lat', 0)
        p_lon = r.geometry.x if hasattr(r, 'geometry') and r.geometry else r.get('lon', 0)

        flow = get_tomtom_flow(p_lat, p_lon)
        time.sleep(0.15) # pausa entre consultas (limite de requisições)

        if flow:
            cur_speed = flow.get('currentSpeed', 0)
            free_speed = flow.get('freeFlowSpeed', max(cur_speed, 60))
            conf = flow.get('confidence', 1.0)
            ratio = cur_speed / free_speed if free_speed > 0 else 1.0
            perda = max(0.0, (1.0 - ratio) * 100)

            if ratio < 0.70:
                status = "Intenso / Retenção Severa"
                cor = "#ef4444"
            elif ratio < 0.88:
                status = "Moderado / Alerta de Fluidez"
                cor = "#f59e0b"
            else:
                status = "Fluidez Plena / Tráfego Livre"
                cor = "#10b981"

            results.append({
                'id': p_id, 'rodovia': p_rod, 'uf': p_uf, 'municipio': p_muni,
                'lat': p_lat, 'lon': p_lon,
                'velocidade_real_kmh': cur_speed, 'velocidade_livre_kmh': free_speed,
                'razao_fluidez': round(ratio, 2), 'perda_pct': round(perda, 1),
                'status_fluxo': status, 'cor_badge': cor, 'confianca': conf
            })
            print(f"  P{p_id:02d} | {p_rod[:15]:15s} | {p_muni[:20]:20s} -> Real: {cur_speed} km/h (Livre: {free_speed} km/h) [{status}]")
        else:
            # Sem resposta da API: valores estimados
            results.append({
                'id': p_id, 'rodovia': p_rod, 'uf': p_uf, 'municipio': p_muni,
                'lat': p_lat, 'lon': p_lon,
                'velocidade_real_kmh': 60, 'velocidade_livre_kmh': 60,
                'razao_fluidez': 1.0, 'perda_pct': 0.0,
                'status_fluxo': 'Fluidez Plena (Estimada)', 'cor_badge': '#10b981', 'confianca': 0.5
            })

    df_out = pd.DataFrame(results)
    df_out.to_csv(cfg['csv_out'], index=False, encoding='utf-8')
    print(f" [OK] Tabela CSV gerada em: {cfg['csv_out']}")

# ==============================================================================
# ETAPA 5: EXECUÇÃO PRINCIPAL
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Medidor Unificado de Velocidades Reais TomTom")
    parser.add_argument('--tipo', choices=['federais', 'estaduais', 'vicinais', 'todas'], default='todas', help="Tipo de portas a processar")
    parser.add_argument('--testar', action='store_true', help="Apenas testa a conexão com a API")
    args = parser.parse_args()

    if args.testar:
        testar_conexao()
        return

    print("Iniciando motor de telemetria TomTom do Produto 4...")
    if args.tipo == 'todas':
        for t in ['federais', 'estaduais', 'vicinais']:
            processar_portas(t)
    else:
        processar_portas(args.tipo)

    print("\n Processamento de telemetria concluído com sucesso!")

if __name__ == '__main__':
    main()
