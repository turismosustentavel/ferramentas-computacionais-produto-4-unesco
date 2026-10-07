# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
FASE 1c - ATRIBUICAO ESPACIAL DOS PONTOS AO MUNICIPIO
================================================================================
OBJETIVO:
    Definir a que municipio cada ponto pertence pela GEOMETRIA - intersecao da
    coordenada do ponto com a malha municipal oficial do IBGE - e nao pelo campo
    de texto preenchido em campo.

POR QUE:
    O campo textual diverge da realidade em pelo menos um caso conhecido: a ficha
    registrada como "Barracao / Acesso viario" corresponde a linha catalogada sob
    Dionisio Cerqueira. Em area de conurbacao transfronteirica o preenchimento
    manual erra com frequencia. A geometria e arbitro objetivo.

ENTRADAS:
    - Malha municipal IBGE 2025 (5.573 municipios, EPSG:4674 / SIRGAS 2000)
    - pontos_afericao_selecionados.csv  (89 pontos, decimal com virgula)
    - georreferenciamento.xlsx, aba 'georreferenciamento' (69 pontos)
    - camadas_qgis/1_pontos_afericao_selecionados.geojson (15 pontos)

SAIDAS:
    02_Dados_Municipais/pontos_atribuicao_espacial.xlsx
    02_Dados_Municipais/pontos_atribuicao_espacial.geojson
================================================================================
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).parent))
from comum import (  # noqa: E402
    ACERVO, CAMPO, JOTFORM, CAMADAS_QGIS, DIR_DADOS, POR_CODIGO,
    normalizar_municipio, parse_coordenadas, coordenada_plausivel,
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

MALHA = (ACERVO / "01_Bases_Secundarias_Oficiais" / "Shapes" /
         "BR_Municipios_2025.zip")
CRS_IBGE = "EPSG:4674"      # SIRGAS 2000
CRS_METRICO = "EPSG:5880"   # SIRGAS 2000 / Brazil Polyconic - para distancias


# ==============================================================================
# 1. LEITURA DAS FONTES DE PONTOS
# ==============================================================================
registros: list[dict] = []

# --- 1.1 CSV oficial de pontos selecionados ----------------------------------
csv_pontos = CAMPO / "03_Pontos_Afericao" / "pontos_afericao_selecionados.csv"
df = pd.read_csv(csv_pontos, encoding="utf-8")
for _, r in df.iterrows():
    lat, lon = parse_coordenadas(r["latitude"], r["longitude"])
    registros.append({
        "fonte": "CSV pontos selecionados",
        "id_origem": f"{r['municipio']} | {r['ordem_ponto']}",
        "nome": r["nome_ponto_afericao"],
        "municipio_declarado": r["municipio"],
        "lat": lat, "lon": lon,
    })
print(f"[1] CSV pontos selecionados ......... {len(df)} registros")

# --- 1.2 Aba 'georreferenciamento' -------------------------------------------
xls = pd.ExcelFile(JOTFORM / "georreferenciamento.xlsx")
dfg = xls.parse("georreferenciamento")
for _, r in dfg.iterrows():
    lat, lon = parse_coordenadas(r["latitude"], r.get("longitude"))
    if not coordenada_plausivel(lat, lon):
        continue
    registros.append({
        "fonte": "Aba georreferenciamento",
        "id_origem": str(r["id"]) if pd.notna(r["id"]) else "",
        "nome": r["nome"] if pd.notna(r["nome"]) else r.get("endereco", ""),
        "municipio_declarado": r["municipio"] if pd.notna(r["municipio"]) else "",
        "lat": lat, "lon": lon,
    })
print(f"[2] Aba georreferenciamento ......... {len(dfg)} linhas "
      f"({sum(1 for x in registros if x['fonte'] == 'Aba georreferenciamento')} com coordenada)")

# --- 1.3 Camada SIG do painel de decisao -------------------------------------
gj = CAMADAS_QGIS / "1_pontos_afericao_selecionados.geojson"
if gj.exists():
    feats = json.loads(gj.read_text(encoding="utf-8"))["features"]
    for f in feats:
        p = f["properties"]
        registros.append({
            "fonte": "Camada SIG do painel",
            "id_origem": f"{p.get('MUNICIPIO')} | {p.get('ORDEM')}",
            "nome": p.get("NOME", ""),
            "municipio_declarado": p.get("MUNICIPIO", ""),
            **dict(zip(("lat", "lon"),
                      parse_coordenadas(p.get("LATITUDE"), p.get("LONGITUDE")))),
        })
    print(f"[3] Camada SIG do painel ............ {len(feats)} feições")

pontos = pd.DataFrame(registros)
sem_coord = pontos[pontos.lat.isna() | pontos.lon.isna()]
pontos = pontos.dropna(subset=["lat", "lon"]).reset_index(drop=True)
print(f"\nTotal georreferenciável: {len(pontos)} pontos "
      f"({len(sem_coord)} descartados por falta de coordenada)")

# ==============================================================================
# 2. MALHA MUNICIPAL
# ==============================================================================
print("\nCarregando malha municipal IBGE 2025 (5.573 municípios)...")
malha = gpd.read_file("/vsizip/" + str(MALHA).replace("\\", "/"))
malha = malha[["CD_MUN", "NM_MUN", "SIGLA_UF", "NM_RGI", "NM_RGINT",
               "AREA_KM2", "geometry"]]
malha["CD_MUN"] = malha["CD_MUN"].astype(int)

gdf = gpd.GeoDataFrame(
    pontos,
    geometry=[Point(xy) for xy in zip(pontos.lon, pontos.lat)],
    crs=CRS_IBGE,
)

# ==============================================================================
# 3. JUNCAO ESPACIAL
# ==============================================================================
print("Executando junção espacial ponto × polígono...")
juncao = gpd.sjoin(gdf, malha, how="left", predicate="within")
juncao = juncao.drop(columns=["index_right"])

# Pontos fora de qualquer municipio brasileiro (territorio estrangeiro ou
# imprecisao de coordenada sobre o rio/linha de fronteira).
fora = juncao[juncao.CD_MUN.isna()].copy()
if len(fora):
    print(f"  {len(fora)} ponto(s) fora da malha brasileira — calculando o "
          f"município mais próximo...")
    malha_m = malha.to_crs(CRS_METRICO)
    fora_m = fora.to_crs(CRS_METRICO)
    prox = gpd.sjoin_nearest(
        fora_m[["geometry"]], malha_m, how="left", distance_col="dist_m")
    for idx, r in prox.iterrows():
        juncao.loc[idx, "CD_MUN"] = r["CD_MUN"]
        juncao.loc[idx, "NM_MUN"] = r["NM_MUN"]
        juncao.loc[idx, "SIGLA_UF"] = r["SIGLA_UF"]
        juncao.loc[idx, "dist_borda_m"] = r["dist_m"]

juncao["CD_MUN"] = juncao["CD_MUN"].astype("Int64")

# ==============================================================================
# 4. COMPARACAO: DECLARADO x GEOMETRICO
# ==============================================================================
def _cod_declarado(t):
    m = normalizar_municipio(t)
    return m.codigo_ibge if m else pd.NA


juncao["cod_declarado"] = juncao["municipio_declarado"].map(_cod_declarado).astype("Int64")
juncao["municipio_geometrico"] = juncao["NM_MUN"] + " (" + juncao["SIGLA_UF"] + ")"
juncao["no_escopo"] = juncao["CD_MUN"].map(lambda c: bool(c) and int(c) in POR_CODIGO)

def _situacao(r):
    if pd.isna(r["CD_MUN"]):
        return "sem município"
    if pd.isna(r["cod_declarado"]):
        return "declarado não reconhecido"
    if int(r["CD_MUN"]) == int(r["cod_declarado"]):
        return "confere"
    return "DIVERGE"


juncao["situacao"] = juncao.apply(_situacao, axis=1)

# --- 4.1 Triagem das divergencias pela distancia ao municipio declarado ------
# A distancia separa tres naturezas distintas de divergencia:
#   <= 500 m  ponto de borda ou conurbacao - a geometria esta certa e o
#             preenchimento tambem faz sentido funcional (a infraestrutura de
#             um municipio esta fisicamente no territorio do vizinho);
#   <= 5 km   caso a revisar - pode ser imprecisao ou equipamento realmente
#             situado no municipio vizinho;
#   > 5 km    erro de geocodificacao - a coordenada nao corresponde ao ponto.
malha_m = malha.to_crs(CRS_METRICO)
juncao_m = juncao.to_crs(CRS_METRICO)
juncao["dist_ao_declarado_m"] = pd.NA
for idx, r in juncao[juncao.situacao == "DIVERGE"].iterrows():
    poly = malha_m.loc[malha_m.CD_MUN == int(r["cod_declarado"]), "geometry"]
    if len(poly):
        juncao.loc[idx, "dist_ao_declarado_m"] = poly.iloc[0].distance(
            juncao_m.geometry.loc[idx])


def _triagem(r):
    if r["situacao"] != "DIVERGE":
        return ""
    d = r["dist_ao_declarado_m"]
    if pd.isna(d):
        return "sem referência"
    if d <= 500:
        return "borda/conurbação"
    if d <= 5000:
        return "revisar"
    return "ERRO GROSSEIRO"


juncao["triagem"] = juncao.apply(_triagem, axis=1)

# ==============================================================================
# 5. RELATORIO
# ==============================================================================
print("\n" + "=" * 78)
print("RESULTADO DA ATRIBUIÇÃO ESPACIAL")
print("=" * 78)
print(juncao.groupby(["fonte", "situacao"]).size().to_string())

div = juncao[juncao.situacao == "DIVERGE"]
if len(div):
    print("\n" + "-" * 78)
    print(f"DIVERGÊNCIAS — {len(div)} ponto(s) em município diferente do declarado")
    print("-" * 78)
    for grupo in ("borda/conurbação", "revisar", "ERRO GROSSEIRO", "sem referência"):
        sub = div[div.triagem == grupo]
        if not len(sub):
            continue
        print(f"\n  >> {grupo.upper()} ({len(sub)})")
        for _, r in sub.sort_values("dist_ao_declarado_m").iterrows():
            d = r["dist_ao_declarado_m"]
            dtxt = (f"{d:,.0f} m" if pd.notna(d) and d < 10000
                    else (f"{d / 1000:,.0f} km" if pd.notna(d) else "—"))
            print(f"     {str(r['nome'])[:50]:<50} {dtxt:>9}")
            print(f"        declarado {r['municipio_declarado']}"
                  f"  ->  geometria {r['municipio_geometrico']}   [{r['fonte']}]")

forad = juncao[~juncao.no_escopo & juncao.CD_MUN.notna()]
if len(forad):
    print("\n" + "-" * 78)
    print(f"PONTOS EM MUNICÍPIOS FORA DO ESCOPO DOS 12 — {len(forad)}")
    print("-" * 78)
    for _, r in forad.iterrows():
        print(f"  {str(r['nome'])[:50]:<50} -> {r['municipio_geometrico']}"
              f"   (declarado: {r['municipio_declarado']})")

# --- Contagem final por municipio do escopo ---------------------------------
print("\n" + "-" * 78)
print("PONTOS POR MUNICÍPIO — ATRIBUIÇÃO GEOMÉTRICA (fonte: CSV oficial)")
print("-" * 78)
csvj = juncao[juncao.fonte == "CSV pontos selecionados"]
for cod, m in POR_CODIGO.items():
    n_geo = int((csvj.CD_MUN == cod).sum())
    n_dec = int((csvj.cod_declarado == cod).sum())
    marca = "" if n_geo == n_dec else f"   <-- declarado: {n_dec}"
    print(f"  {m.nome_uf:<26} {n_geo:>3}{marca}")

# ==============================================================================
# 6. GRAVACAO
# ==============================================================================
DIR_DADOS.mkdir(parents=True, exist_ok=True)
saida = juncao.drop(columns=["geometry"]).copy()
saida = saida.rename(columns={
    "CD_MUN": "cod_ibge_geometrico", "NM_MUN": "nome_geometrico",
    "SIGLA_UF": "uf_geometrica", "NM_RGI": "regiao_imediata",
    "NM_RGINT": "regiao_intermediaria"})
colunas = ["fonte", "id_origem", "nome", "municipio_declarado", "cod_declarado",
           "cod_ibge_geometrico", "nome_geometrico", "uf_geometrica",
           "regiao_imediata", "regiao_intermediaria", "lat", "lon",
           "situacao", "triagem", "dist_ao_declarado_m", "no_escopo"]
if "dist_borda_m" in saida.columns:
    colunas.append("dist_borda_m")
saida = saida[[c for c in colunas if c in saida.columns]]

xlsx = DIR_DADOS / "pontos_atribuicao_espacial.xlsx"
with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
    saida.to_excel(w, sheet_name="Atribuição", index=False)
    if len(div):
        div_out = saida.loc[div.index]
        div_out.to_excel(w, sheet_name="Divergências", index=False)
    if len(sem_coord):
        sem_coord.to_excel(w, sheet_name="Sem coordenada", index=False)

geoj = DIR_DADOS / "pontos_atribuicao_espacial.geojson"
juncao.to_file(geoj, driver="GeoJSON")

print(f"\nPlanilha gravada em: {xlsx}")
print(f"Camada gravada em:  {geoj}")
