# -*- coding: utf-8 -*-
"""
================================================================================
PROJETO UNESCO UNES 2369/2025 | ITAIPU PARQUETEC - TS.DTUR
PRODUTO 4: DIAGNÓSTICO REGIONAL DE INFRAESTRUTURA, MOBILIDADE E CONECTIVIDADE
================================================================================
MÓDULO 01: TRANSPORTE RODOVIÁRIO COLETIVO E TERMINAIS
SCRIPT: mapeador_terminais_rodoviarios.py
--------------------------------------------------------------------------------
O QUE FAZ:
    Monta o cadastro georreferenciado dos terminais rodoviários da Faixa de
    Fronteira do PR e do MS e associa a cada terminal o movimento anual de
    passageiros interestaduais:
      1) Lê a planilha de bilhetagem da ANTT e corrige grafias corrompidas
         de nomes de municípios ('?' no lugar de caracteres acentuados) por
         meio do dicionário `corrupted_map`.
      2) Normaliza cada nome para a chave "MUNICIPIO/UF" (sem acento,
         maiúsculo) e soma os bilhetes por município de origem (embarques)
         e por município de destino (desembarques).
      3) Cruza essas somas com a lista de terminais escrita no script
         (`terminals_raw`: município, UF, nome do terminal, coordenadas,
         rodovias de acesso e perfil funcional). Município sem registro na
         planilha recebe zero.
      4) Classifica cada terminal pelo total de passageiros (embarques +
         desembarques):
             total >= 50.000            Mega Terminal
             10.000 <= total < 50.000   Grande Porte
             2.000 <= total < 10.000    Médio Porte
             0 < total < 2.000          Pequeno Porte / Regional
             total = 0                  Terminal Intermunicipal / Conexão Regional
         e grava a classe no campo `classe_movimento`.
      5) Exporta a camada de pontos (EPSG:4326) em GeoJSON, CSV e Shapefile,
         e compacta o Shapefile em ZIP.

ENTRADAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/08_transporte_coletivo_rodoviarias_clickbus/
        cidades_fronteira_2025.xlsx
        Colunas usadas: ponto_origem_viagem e ponto_destino_viagem (no
        formato "Município/UF") e quantidade_bilhetes.
        Fonte: extrato de bilhetagem do transporte rodoviário interestadual
        de passageiros da ANTT (conjunto "Monitriip Bilhetes de Passagem").
        Portal de dados abertos da ANTT: https://dados.antt.gov.br/
    Cadastro de terminais (nome, coordenadas, rodovias de acesso, perfil)
    escrito no próprio script.

SAÍDAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/08_transporte_coletivo_rodoviarias_clickbus/
        rodoviarias_faixa_fronteira_pr_ms.geojson
        rodoviarias_faixa_fronteira_pr_ms.csv               (UTF-8 com BOM)
        rodoviarias_faixa_fronteira_pr_ms_shp/rodoviarias_faixa_fronteira_pr_ms.shp
            (nomes de campo abreviados para o limite de 10 caracteres)
        rodoviarias_faixa_fronteira_pr_ms_shp.zip

VARIÁVEIS DE AMBIENTE:
    P4_DADOS  (opcional) raiz da árvore de dados; padrão: `dados/` na raiz
              do repositório.

COMO EXECUTAR:
    python regional/01_onibus_terminais_clickbus/mapeador_terminais_rodoviarios.py
================================================================================
"""

# ==============================================================================
# ETAPA 1: IMPORTAÇÃO DE PACOTES
# ==============================================================================

import os
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import unicodedata
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _caminhos import PRODUCAO

sys.stdout.reconfigure(encoding='utf-8')


# ==============================================================================
# ETAPA 2: DIRETÓRIOS
# ==============================================================================
prod_out_dir = str(PRODUCAO)
bus_folder = os.path.join(prod_out_dir, "08_transporte_coletivo_rodoviarias_clickbus")

# ==============================================================================
# ETAPA 3: BILHETAGEM DA ANTT E NORMALIZAÇÃO DE NOMES
# ==============================================================================
# 1. Leitura da planilha de passageiros (ANTT, 2025)
xlsx_path = os.path.join(bus_folder, "cidades_fronteira_2025.xlsx")
df_antt = pd.read_excel(xlsx_path)

# Grafias corrompidas na planilha de origem ('?' no lugar de caracteres
# acentuados) e a grafia correta correspondente.
corrupted_map = {
    'Barrac?o': 'Barracão',
    'Campo Mour?o': 'Campo Mourão',
    'Francisco Beltr?o': 'Francisco Beltrão',
    'Marechal C?ndido Rondon': 'Marechal Cândido Rondon',
    'Santo Ant?nio do Sudoeste': 'Santo Antônio do Sudoeste',
    'Capit?o Le?nidas Marques': 'Capitão Leônidas Marques',
    'Navira?': 'Naviraí',
    'Brasil?ndia': 'Brasilândia',
    'C?u Azul': 'Céu Azul',
    'Clevel?ndia': 'Clevelândia',
    'Diamante do Norte': 'Diamante do Norte',
    'Guarania?u': 'Guaraniaçu',
    'Gua?ra': 'Guaíra',
    'Maring?': 'Maringá',
    'Mari?polis': 'Mariópolis',
    'Matel?ndia': 'Matelândia',
    'P?rola d\'Oeste': 'Pérola d\'Oeste',
    'Paranava?': 'Paranavaí',
    'Planaltina do Paran?': 'Planaltina do Paraná',
    'Renascen?a': 'Renascença',
    'S?o Gabriel do Oeste': 'São Gabriel do Oeste',
    'S?o Miguel do Igua?u': 'São Miguel do Iguaçu',
    'Santa Isabel do Iva?': 'Santa Isabel do Ivaí',
    'Tr?s Lagoas': 'Três Lagoas',
    'Ubirat?': 'Ubiratã',
    'Foz do Igua?u': 'Foz do Iguaçu',
    'Amp?re': 'Ampére'
}

def normalize_city_uf(name_uf):
    """Converte "Município/UF" na chave "MUNICIPIO/UF" (sem acento, maiúsculo),
    corrigindo antes as grafias listadas em `corrupted_map`."""
    if not isinstance(name_uf, str):
        return ""
    parts = name_uf.split('/')
    city = parts[0].strip()
    uf = parts[1].strip().upper() if len(parts) > 1 else ""
    
    for k, v in corrupted_map.items():
        if k.lower() == city.lower():
            city = v
            break
            
    nfkd = unicodedata.normalize('NFKD', city).encode('ASCII', 'ignore').decode('ASCII').strip().upper()
    return f"{nfkd}/{uf}"

df_antt['orig_clean_uf'] = df_antt['ponto_origem_viagem'].apply(normalize_city_uf)
df_antt['dest_clean_uf'] = df_antt['ponto_destino_viagem'].apply(normalize_city_uf)

# Bilhetes somados por município de origem (embarques) e de destino (desembarques)
orig_agg = df_antt.groupby('orig_clean_uf')['quantidade_bilhetes'].sum().to_dict()
dest_agg = df_antt.groupby('dest_clean_uf')['quantidade_bilhetes'].sum().to_dict()

# ==============================================================================
# ETAPA 4: CADASTRO DE TERMINAIS E CLASSIFICAÇÃO POR MOVIMENTO
# ==============================================================================
# 2. Terminais rodoviários da Faixa de Fronteira do PR e do MS.
#    Campos: cidade, uf, nome, lat, lon (graus, WGS 84), rodovias de acesso e
#    perfil funcional (tipo).
terminals_raw = [
    # --- MATO GROSSO DO SUL ---
    {"cidade": "Campo Grande", "uf": "MS", "nome": "Terminal Rodoviário Senador Antônio Mendes Canale", "lat": -20.5284, "lon": -54.6298, "rodovias": "BR-163 / BR-262 / BR-060", "tipo": "Hub Metropolitano / Capital"},
    {"cidade": "Dourados", "uf": "MS", "nome": "Terminal Rodoviário Renato Lemes Soares", "lat": -22.2173, "lon": -54.7938, "rodovias": "BR-163 / MS-156 / MS-276", "tipo": "Polo Regional Sul MS"},
    {"cidade": "Corumbá", "uf": "MS", "nome": "Terminal Rodoviário Intermunicipal de Corumbá", "lat": -19.0152, "lon": -57.6538, "rodovias": "BR-262", "tipo": "Fronteira Internacional / Pantanal"},
    {"cidade": "Ponta Porã", "uf": "MS", "nome": "Terminal Rodoviário de Ponta Porã", "lat": -22.5312, "lon": -55.7185, "rodovias": "BR-463 / MS-164", "tipo": "Fronteira Internacional / Cidade Gêmea"},
    {"cidade": "Bonito", "uf": "MS", "nome": "Terminal Rodoviário de Bonito", "lat": -21.1278, "lon": -56.4829, "rodovias": "MS-382 / MS-178 / MS-345", "tipo": "Polo Ecoturístico"},
    {"cidade": "Porto Murtinho", "uf": "MS", "nome": "Terminal Rodoviário de Porto Murtinho", "lat": -21.6989, "lon": -57.8825, "rodovias": "BR-267 (Rota Bioceânica)", "tipo": "Fronteira / Hidrovia"},
    {"cidade": "Mundo Novo", "uf": "MS", "nome": "Terminal Rodoviário de Mundo Novo", "lat": -23.9400, "lon": -54.2708, "rodovias": "BR-163", "tipo": "Fronteira Internacional / Cone Sul"},
    {"cidade": "Naviraí", "uf": "MS", "nome": "Terminal Rodoviário de Naviraí", "lat": -23.0645, "lon": -54.1982, "rodovias": "BR-163 / MS-141", "tipo": "Polo Agroindustrial"},
    {"cidade": "Nova Andradina", "uf": "MS", "nome": "Terminal Rodoviário de Nova Andradina", "lat": -22.2356, "lon": -53.3442, "rodovias": "BR-376 / MS-276", "tipo": "Polo Regional"},
    {"cidade": "Ivinhema", "uf": "MS", "nome": "Terminal Rodoviário de Ivinhema", "lat": -22.3082, "lon": -53.8189, "rodovias": "BR-376 / MS-141", "tipo": "Regional Vale do Ivinhema"},
    {"cidade": "Sidrolândia", "uf": "MS", "nome": "Terminal Rodoviário de Sidrolândia", "lat": -20.9318, "lon": -54.9612, "rodovias": "BR-060 / MS-162", "tipo": "Transição Faixa de Fronteira"},
    {"cidade": "Maracaju", "uf": "MS", "nome": "Terminal Rodoviário de Maracaju", "lat": -21.6145, "lon": -55.1382, "rodovias": "BR-267 / MS-162", "tipo": "Polo Graneleiro"},
    {"cidade": "Miranda", "uf": "MS", "nome": "Terminal Rodoviário de Miranda", "lat": -20.2415, "lon": -56.3789, "rodovias": "BR-262", "tipo": "Portal do Pantanal"},
    {"cidade": "Anastácio", "uf": "MS", "nome": "Terminal Rodoviário de Anastácio / Aquidauana", "lat": -20.4851, "lon": -55.8089, "rodovias": "BR-262 / BR-419", "tipo": "Portal do Pantanal"},
    {"cidade": "Bodoquena", "uf": "MS", "nome": "Terminal Rodoviário de Bodoquena", "lat": -20.5389, "lon": -56.7172, "rodovias": "MS-339", "tipo": "Polo Ecoturístico"},
    {"cidade": "Bela Vista", "uf": "MS", "nome": "Terminal Rodoviário de Bela Vista", "lat": -22.1092, "lon": -56.5218, "rodovias": "BR-060", "tipo": "Fronteira Internacional / Cidade Gêmea"},
    {"cidade": "Amambai", "uf": "MS", "nome": "Terminal Rodoviário de Amambai", "lat": -23.1042, "lon": -55.2256, "rodovias": "MS-156 / MS-289", "tipo": "Tronco Cone Sul"},
    {"cidade": "Coronel Sapucaia", "uf": "MS", "nome": "Terminal Rodoviário de Coronel Sapucaia", "lat": -23.2715, "lon": -55.5312, "rodovias": "MS-165 / MS-289", "tipo": "Fronteira Seca Internacional"},
    {"cidade": "Paranhos", "uf": "MS", "nome": "Terminal Rodoviário de Paranhos", "lat": -23.8925, "lon": -55.4312, "rodovias": "MS-165 / MS-295", "tipo": "Fronteira Seca Internacional"},
    {"cidade": "Sete Quedas", "uf": "MS", "nome": "Terminal Rodoviário de Sete Quedas", "lat": -23.9712, "lon": -55.0389, "rodovias": "MS-165 / MS-156", "tipo": "Fronteira Seca Internacional"},
    {"cidade": "Japorã", "uf": "MS", "nome": "Terminal Rodoviário de Japorã", "lat": -23.8812, "lon": -54.4089, "rodovias": "MS-299 / MS-386", "tipo": "Fronteira Internacional"},
    {"cidade": "Brasilândia", "uf": "MS", "nome": "Terminal Rodoviário de Brasilândia", "lat": -21.2582, "lon": -52.0382, "rodovias": "MS-395 / BR-158", "tipo": "Transição Leste MS"},
    {"cidade": "Ribas do Rio Pardo", "uf": "MS", "nome": "Terminal Rodoviário de Ribas do Rio Pardo", "lat": -20.4482, "lon": -53.7582, "rodovias": "BR-262", "tipo": "Polo de Celulose"},

    # --- PARANÁ ---
    {"cidade": "Foz do Iguaçu", "uf": "PR", "nome": "Terminal Rodoviário Internacional de Foz do Iguaçu", "lat": -25.5186, "lon": -54.5682, "rodovias": "BR-277 / BR-469", "tipo": "Hub Internacional / Turístico"},
    {"cidade": "Medianeira", "uf": "PR", "nome": "Terminal Rodoviário de Medianeira", "lat": -25.2982, "lon": -54.0932, "rodovias": "BR-277 / PR-495", "tipo": "Polo Intermediário Oeste"},
    {"cidade": "Umuarama", "uf": "PR", "nome": "Terminal Rodoviário de Umuarama", "lat": -23.7652, "lon": -53.3182, "rodovias": "PR-323 / PR-482 / PR-489", "tipo": "Polo Regional Noroeste"},
    {"cidade": "Cascavel", "uf": "PR", "nome": "Terminal Rodoviário Dra. Helenise Tolentino Pinheiro", "lat": -24.9682, "lon": -53.4752, "rodovias": "BR-277 / BR-163 / BR-467 / BR-369", "tipo": "Hub Regional / Entroncamento Troncal"},
    {"cidade": "Guaíra", "uf": "PR", "nome": "Terminal Rodoviário de Guaíra", "lat": -24.0812, "lon": -54.2512, "rodovias": "BR-163 / BR-272", "tipo": "Fronteira Internacional / Ponte Ayrton Senna"},
    {"cidade": "Capanema", "uf": "PR", "nome": "Terminal Rodoviário de Capanema", "lat": -25.6682, "lon": -53.8012, "rodovias": "BR-163 / PR-281", "tipo": "Fronteira Turística / PNI"},
    {"cidade": "Toledo", "uf": "PR", "nome": "Terminal Rodoviário de Toledo (Alcido Pastre)", "lat": -24.7182, "lon": -53.7412, "rodovias": "BR-163 / PR-317 / PR-585", "tipo": "Polo Agroindustrial"},
    {"cidade": "Marechal Cândido Rondon", "uf": "PR", "nome": "Terminal Rodoviário de Marechal Cândido Rondon", "lat": -24.5512, "lon": -54.0582, "rodovias": "BR-163 / PR-491", "tipo": "Polo Agroindustrial"},
    {"cidade": "Pato Branco", "uf": "PR", "nome": "Terminal Rodoviário Municipal de Pato Branco", "lat": -26.2252, "lon": -52.6712, "rodovias": "PR-280 / PR-493 / BR-158", "tipo": "Polo Regional Sudoeste"},
    {"cidade": "Francisco Beltrão", "uf": "PR", "nome": "Terminal Rodoviário Prefeito João Batista de Arruda", "lat": -26.0782, "lon": -53.0512, "rodovias": "PR-180 / PR-483 / PR-566", "tipo": "Polo Regional Sudoeste"},
    {"cidade": "Realeza", "uf": "PR", "nome": "Terminal Rodoviário de Realeza", "lat": -25.7682, "lon": -53.5312, "rodovias": "PR-182 / PR-281", "tipo": "Entroncamento Sudoeste"},
    {"cidade": "Santo Antônio do Sudoeste", "uf": "PR", "nome": "Terminal Rodoviário de Santo Antônio do Sudoeste", "lat": -26.0712, "lon": -53.7252, "rodovias": "BR-163", "tipo": "Fronteira Internacional Argentina"},
    {"cidade": "Campo Mourão", "uf": "PR", "nome": "Terminal Rodoviário de Campo Mourão", "lat": -24.0412, "lon": -52.3812, "rodovias": "BR-487 / BR-272 / BR-369", "tipo": "Polo Regional / Estrada Boiadeira"},
    {"cidade": "Palotina", "uf": "PR", "nome": "Terminal Rodoviário de Palotina", "lat": -24.2812, "lon": -53.8382, "rodovias": "PR-182 / PR-364", "tipo": "Polo Agroindustrial"},
    {"cidade": "Barracão", "uf": "PR", "nome": "Terminal Rodoviário de Barracão / Dionísio Cerqueira", "lat": -26.2512, "lon": -53.6312, "rodovias": "BR-163", "tipo": "Trifronteira PR/SC/Argentina"},
    {"cidade": "Nova Londrina", "uf": "PR", "nome": "Terminal Rodoviário de Nova Londrina", "lat": -22.7652, "lon": -52.9882, "rodovias": "PR-182 / BR-376", "tipo": "Extremo Noroeste PR"},
    {"cidade": "Pranchita", "uf": "PR", "nome": "Terminal Rodoviário de Pranchita", "lat": -26.0212, "lon": -53.7382, "rodovias": "BR-163", "tipo": "Fronteira Sudoeste"},
    {"cidade": "Planalto", "uf": "PR", "nome": "Terminal Rodoviário de Planalto", "lat": -25.7182, "lon": -53.7682, "rodovias": "PR-281", "tipo": "Regional Sudoeste"},
    {"cidade": "Diamante do Norte", "uf": "PR", "nome": "Terminal Rodoviário de Diamante do Norte", "lat": -22.6582, "lon": -52.8612, "rodovias": "PR-182", "tipo": "Vale do Paranapanema"},
    {"cidade": "Capitão Leônidas Marques", "uf": "PR", "nome": "Terminal Rodoviário de Capitão Leônidas Marques", "lat": -25.4812, "lon": -53.6182, "rodovias": "BR-163", "tipo": "Corredor BR-163 Sudoeste"},
    {"cidade": "Loanda", "uf": "PR", "nome": "Terminal Rodoviário de Loanda", "lat": -22.9282, "lon": -53.1382, "rodovias": "PR-182 / PR-218", "tipo": "Polo Arenito Caiuá"},
    {"cidade": "Marmeleiro", "uf": "PR", "nome": "Terminal Rodoviário de Marmeleiro", "lat": -26.1482, "lon": -53.0282, "rodovias": "BR-280 / PR-180", "tipo": "Entroncamento Sudoeste"},
    {"cidade": "Santa Terezinha de Itaipu", "uf": "PR", "nome": "Terminal Rodoviário de Santa Terezinha de Itaipu", "lat": -25.4382, "lon": -54.3982, "rodovias": "BR-277", "tipo": "Corredor Turístico BR-277"},
    {"cidade": "Laranjeiras do Sul", "uf": "PR", "nome": "Terminal Rodoviário de Laranjeiras do Sul", "lat": -25.4082, "lon": -52.4182, "rodovias": "BR-277 / PR-158", "tipo": "Transição Faixa de Fronteira"},
    {"cidade": "Clevelândia", "uf": "PR", "nome": "Terminal Rodoviário de Clevelândia", "lat": -26.4082, "lon": -52.4712, "rodovias": "PR-280 / PR-459", "tipo": "Corredor Sul PR-280"},
    {"cidade": "Palmas", "uf": "PR", "nome": "Terminal Rodoviário de Palmas", "lat": -26.4812, "lon": -51.9882, "rodovias": "PR-280 / PR-449", "tipo": "Polo Sul Paranaense"},
    {"cidade": "Porto Rico", "uf": "PR", "nome": "Terminal Rodoviário de Porto Rico", "lat": -22.7712, "lon": -53.2682, "rodovias": "PR-218 / Balneários Rio Paraná", "tipo": "Polo Ecoturístico / Náutico"},
    {"cidade": "Cianorte", "uf": "PR", "nome": "Terminal Rodoviário de Cianorte", "lat": -23.6582, "lon": -52.6082, "rodovias": "PR-323 / PR-082", "tipo": "Polo Vestuário / Noroeste"},
    {"cidade": "Paranavaí", "uf": "PR", "nome": "Terminal Rodoviário Urbano e Intermunicipal de Paranavaí", "lat": -23.0782, "lon": -52.4612, "rodovias": "BR-376 / PR-218", "tipo": "Polo Regional Arenito Caiuá"}
]

# Passageiros por terminal, pela chave normalizada "MUNICIPIO/UF"
stations_enriched = []
for t in terminals_raw:
    key = normalize_city_uf(f"{t['cidade']}/{t['uf']}")

    emb = orig_agg.get(key, 0)
    des = dest_agg.get(key, 0)
    total_pax = emb + des

    # Classe de movimento pelo total anual de passageiros
    if total_pax >= 50000:
        cat_mov = "Mega Terminal (> 50k pax/ano)"
    elif total_pax >= 10000:
        cat_mov = "Grande Porte (10k a 50k pax/ano)"
    elif total_pax >= 2000:
        cat_mov = "Médio Porte (2k a 10k pax/ano)"
    elif total_pax > 0:
        cat_mov = "Pequeno Porte / Regional (< 2k pax/ano)"
    else:
        cat_mov = "Terminal Intermunicipal / Conexão Regional"

    stations_enriched.append({
        'id': len(stations_enriched) + 1,
        'cidade': t['cidade'],
        'uf': t['uf'],
        'nome_terminal': t['nome'],
        'rodovias_acesso': t['rodovias'],
        'perfil_funcional': t['tipo'],
        'lat': t['lat'],
        'lon': t['lon'],
        'pax_embarque_2025': emb,
        'pax_desembarque_2025': des,
        'pax_total_2025': total_pax,
        'classe_movimento': cat_mov,
        'geometry': Point(t['lon'], t['lat'])
    })

gdf_stations = gpd.GeoDataFrame(stations_enriched, crs='EPSG:4326')

print("--- CLASSIFICAÇÃO DOS TERMINAIS RODOVIÁRIOS (ANTT 2025) ---")
print(gdf_stations[['cidade', 'uf', 'pax_total_2025', 'classe_movimento']].sort_values(by='pax_total_2025', ascending=False).to_string())

# ==============================================================================
# ETAPA 5: EXPORTAÇÃO
# ==============================================================================
# 3. Exportação para a pasta do módulo
os.makedirs(bus_folder, exist_ok=True)

# GeoJSON
out_geojson = os.path.join(bus_folder, "rodoviarias_faixa_fronteira_pr_ms.geojson")
gdf_stations.to_file(out_geojson, driver='GeoJSON')

# CSV
out_csv = os.path.join(bus_folder, "rodoviarias_faixa_fronteira_pr_ms.csv")
gdf_stations.drop(columns=['geometry']).to_csv(out_csv, index=False, encoding='utf-8-sig')

# Shapefile (nomes de campo com até 10 caracteres) e pacote ZIP
shp_dir = os.path.join(bus_folder, "rodoviarias_faixa_fronteira_pr_ms_shp")
os.makedirs(shp_dir, exist_ok=True)
gdf_shp = gdf_stations.copy()
gdf_shp.columns = ['id', 'cidade', 'uf', 'nome_term', 'rodovias', 'perfil', 'lat', 'lon', 'pax_emb', 'pax_des', 'pax_tot', 'classe_mov', 'geometry']
shp_path = os.path.join(shp_dir, "rodoviarias_faixa_fronteira_pr_ms.shp")
gdf_shp.to_file(shp_path, driver='ESRI Shapefile', encoding='utf-8')

zip_path = os.path.join(bus_folder, "rodoviarias_faixa_fronteira_pr_ms_shp.zip")
shutil.make_archive(zip_path.replace('.zip', ''), 'zip', shp_dir)

print(f"\nArquivos vetoriais e tabulares atualizados em:\n  {bus_folder}")
