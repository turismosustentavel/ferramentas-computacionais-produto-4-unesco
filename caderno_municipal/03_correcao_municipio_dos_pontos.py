# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
FASE 1c - CORRECAO DA ATRIBUICAO MUNICIPAL DOS PONTOS
================================================================================
Aplica as regras de decisao definidas com a coordenacao do estudo sobre as
divergencias entre o municipio declarado em campo e o municipio obtido pela
geometria (malha IBGE 2025).

REGRAS
------
R1. Divergencia entre DOIS municipios do escopo dos 12
    -> prevalece a GEOMETRIA. O preenchimento foi uma escolha de campo, e a
       escolha errou. Excecao nominal: o Terminal Rodoviario de Dionisio
       Cerqueira permanece em Dionisio Cerqueira, ainda que o equipamento
       esteja fisicamente em territorio de Barracao.

R2. Geometria aponta municipio FORA do escopo dos 12
    -> prevalece o DECLARADO. O ponto existe para representar a porta de
       acesso de um dos 12 municipios visitados; que ela caia no territorio
       do vizinho e parte do achado, nao motivo de reatribuicao.

R3. Coordenada invalida (erro de geocodificacao)
    -> a coordenada e recuperada, nao o municipio:
       a) equipamento com localizacao conhecida em outra fonte -> reusa;
       b) ponto de acesso rodoviario -> intersecao do eixo da rodovia
          declarada com o limite municipal, tomando o cruzamento mais
          distante da sede urbana, do lado declarado;
       c) travessia internacional corretamente posicionada, apenas em
          territorio do municipio vizinho -> mantem declarado e coordenada.

SAIDAS
------
    02_Dados_Municipais/pontos_municipio_corrigido.xlsx
    02_Dados_Municipais/pontos_municipio_corrigido.geojson
================================================================================
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).parent))
from comum import ACERVO, PRODUCAO, DIR_DADOS, POR_CODIGO  # noqa: E402

warnings.filterwarnings("ignore", message=".*geographic CRS.*")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

MALHA = (ACERVO / "01_Bases_Secundarias_Oficiais" / "Shapes" /
         "BR_Municipios_2025.zip")
SNV = (PRODUCAO / "02_malha_rodoviaria_nacional_dnit_snv_shp" / "vw_snv_rod.shp")
CRS_M = "EPSG:5880"

COD_DC = 4205001      # Dionisio Cerqueira (SC)
COD_BAR = 4102604     # Barracao (PR)

# Sede urbana aproximada de Dionisio Cerqueira, usada como referencia de
# distancia para escolher o cruzamento de acesso.
SEDE_DC = Point(-53.6383, -26.2566)


# ==============================================================================
# 1. BASES
# ==============================================================================
print("Carregando malha municipal e malha rodoviaria federal...")
malha = gpd.read_file("/vsizip/" + str(MALHA).replace("\\", "/"))
malha["CD_MUN"] = malha["CD_MUN"].astype(int)
snv = gpd.read_file(SNV)
snv["Codigo_BR"] = pd.to_numeric(snv["Codigo_BR"], errors="coerce")

df = pd.read_excel(DIR_DADOS / "pontos_atribuicao_espacial.xlsx",
                   sheet_name="Atribuição")


# ==============================================================================
# 2. R3b - RECUPERACAO DE COORDENADA POR INTERSECAO RODOVIA x LIMITE
# ==============================================================================
def acesso_rodoviario(cod_mun: int, br: int, sede: Point,
                      excluir_uf: str | None = None,
                      exigir_uf: str | None = None) -> tuple[float, float, str]:
    """Cruzamento do eixo da BR com o limite municipal mais distante da sede.

    `exigir_uf` restringe aos cruzamentos cujo municipio confrontante esta na
    UF indicada - e assim que se distingue "acesso pelo Parana" de "acesso
    pelo interior de Santa Catarina" quando a rodovia margeia a divisa.
    """
    poly = malha.loc[malha.CD_MUN == cod_mun, "geometry"].iloc[0]
    eixo = unary_union(snv.loc[snv.Codigo_BR == br, "geometry"].tolist())
    cruz = eixo.intersection(poly.boundary)
    geoms = list(cruz.geoms) if hasattr(cruz, "geoms") else [cruz]
    cands = [g.centroid for g in geoms if not g.is_empty]
    if not cands:
        raise RuntimeError(f"BR-{br} nao cruza o limite de {cod_mun}")

    viz = malha[malha.geometry.touches(poly)]
    viz_m = viz.to_crs(CRS_M)

    filtrados = []
    for p in cands:
        pm = gpd.GeoSeries([p], crs="EPSG:4674").to_crs(CRS_M).iloc[0]
        perto = viz_m[viz_m.geometry.distance(pm) < 200]
        ufs = set(perto.SIGLA_UF)
        if exigir_uf and exigir_uf not in ufs:
            continue
        if excluir_uf and ufs == {excluir_uf}:
            continue
        filtrados.append((p, sorted({f"{r.NM_MUN}/{r.SIGLA_UF}"
                                     for _, r in perto.iterrows()})))
    if not filtrados:
        filtrados = [(p, []) for p in cands]

    sede_m = gpd.GeoSeries([sede], crs="EPSG:4674").to_crs(CRS_M).iloc[0]
    melhor, viz_nome = max(
        filtrados,
        key=lambda t: gpd.GeoSeries([t[0]], crs="EPSG:4674")
        .to_crs(CRS_M).iloc[0].distance(sede_m))
    d = gpd.GeoSeries([melhor], crs="EPSG:4674").to_crs(CRS_M).iloc[0].distance(sede_m)
    return melhor.y, melhor.x, f"BR-{br} × limite municipal, a {d/1000:.1f} km da sede; confronta {', '.join(viz_nome) or 'n/d'}"


print("\nRecuperando coordenadas dos acessos rodoviários de Dionísio Cerqueira...")
acesso_163 = acesso_rodoviario(COD_DC, 163, SEDE_DC, exigir_uf="SC")
acesso_373 = acesso_rodoviario(COD_DC, 373, SEDE_DC, exigir_uf="PR")
print(f"  BR-163 (via São Miguel do Oeste): {acesso_163[0]:.6f}, {acesso_163[1]:.6f}")
print(f"           {acesso_163[2]}")
print(f"  BR-373 (acesso pelo Paraná):      {acesso_373[0]:.6f}, {acesso_373[1]:.6f}")
print(f"           {acesso_373[2]}")

# Terminal rodoviario de Dionisio Cerqueira: a localizacao correta ja consta
# do CSV oficial de pontos de afericao.
rodov_dc = df[(df.nome.astype(str).str.contains("Rodoviária de Dionísio", na=False))]
COORD_RODOV_DC = (float(rodov_dc.lat.iloc[0]), float(rodov_dc.lon.iloc[0]))
print(f"  Terminal rodoviário de DC:        {COORD_RODOV_DC[0]:.6f}, "
      f"{COORD_RODOV_DC[1]:.6f}  (reaproveitado do CSV oficial)")


# ==============================================================================
# 3. CORRECOES NOMINAIS (R1 excecao e R3)
# ==============================================================================
# chave: trecho identificador do nome do ponto
NOMINAIS: dict[str, dict] = {
    "Rodoviária de Dionísio": {
        "regra": "R1-exceção",
        "cod_final": COD_DC,
        "nota": "Terminal fisicamente em Barracão (PR), a 177 m da divisa; "
                "mantido em Dionísio Cerqueira por decisão do estudo.",
    },
    "Rodoviária / Terminal Rodoviário Municipal": {
        "regra": "R3a",
        "cod_final": COD_DC,
        "coord": COORD_RODOV_DC,
        "nota": "Geocodificação resolveu para Goioxim (PR), a 173 km, porque o "
                "endereço declarava 'Dionísio Cerqueira, PR' — o município é de "
                "SC. Coordenada substituída pela do terminal no CSV oficial.",
    },
    "BR-163 (acesso via São Miguel do Oeste": {
        "regra": "R3b",
        "cod_final": COD_DC,
        "coord": (acesso_163[0], acesso_163[1]),
        "nota": "Geocodificação resolveu para São Miguel do Oeste (SC), a 34 km, "
                "pela mesma troca de UF no endereço. Coordenada recalculada: "
                + acesso_163[2],
    },
    "BR-373 / acesso pela região de fronteira": {
        "regra": "R3b",
        "cod_final": COD_DC,
        "coord": (acesso_373[0], acesso_373[1]),
        "nota": "Geocodificação resolveu para Guarapuava (PR), a 227 km, pela "
                "mesma troca de UF no endereço. Coordenada recalculada: "
                + acesso_373[2],
    },
    "Fronteira Brasil–Paraguai (Salto del Guairá)": {
        "regra": "R3c",
        "cod_final": 4108809,   # Guaira (PR)
        "nota": "Não é erro: trata-se da aduana da travessia para Salto del "
                "Guairá, situada entre Guaíra e Mundo Novo. Coordenada válida; "
                "município funcional mantido em Guaíra.",
    },
}


def aplicar(r: pd.Series) -> pd.Series:
    nome = str(r["nome"])
    cod_dec = r["cod_declarado"]
    cod_geo = r["cod_ibge_geometrico"]
    lat, lon = r["lat"], r["lon"]

    # --- correcoes nominais -------------------------------------------------
    for chave, cfg in NOMINAIS.items():
        if chave in nome:
            if "coord" in cfg:
                lat, lon = cfg["coord"]
            return pd.Series({
                "cod_municipio_final": cfg["cod_final"],
                "lat_final": lat, "lon_final": lon,
                "regra": cfg["regra"], "nota_decisao": cfg["nota"],
            })

    # --- sem divergencia ----------------------------------------------------
    if r["situacao"] != "DIVERGE":
        return pd.Series({
            "cod_municipio_final": cod_dec if pd.notna(cod_dec) else cod_geo,
            "lat_final": lat, "lon_final": lon,
            "regra": "", "nota_decisao": "",
        })

    geo_no_escopo = pd.notna(cod_geo) and int(cod_geo) in POR_CODIGO

    # --- R1: divergencia entre dois dos 12 -> vale a geometria --------------
    if geo_no_escopo:
        return pd.Series({
            "cod_municipio_final": int(cod_geo),
            "lat_final": lat, "lon_final": lon,
            "regra": "R1",
            "nota_decisao": (
                f"Declarado {POR_CODIGO[int(cod_dec)].nome_uf}; reatribuído a "
                f"{POR_CODIGO[int(cod_geo)].nome_uf} pela geometria "
                f"({r['dist_ao_declarado_m']:.0f} m de distância)."),
        })

    # --- R2: geometria fora dos 12 -> vale o declarado ----------------------
    return pd.Series({
        "cod_municipio_final": int(cod_dec) if pd.notna(cod_dec) else pd.NA,
        "lat_final": lat, "lon_final": lon,
        "regra": "R2",
        "nota_decisao": (
            f"Situado em {r['nome_geometrico']} ({r['uf_geometrica']}), fora do "
            f"escopo dos 12; mantido em {POR_CODIGO[int(cod_dec)].nome_uf} por "
            f"representar sua porta de acesso."),
    })


df = pd.concat([df, df.apply(aplicar, axis=1)], axis=1)
df["municipio_final"] = df["cod_municipio_final"].map(
    lambda c: POR_CODIGO[int(c)].nome_uf if pd.notna(c) and int(c) in POR_CODIGO else "")


# ==============================================================================
# 4. RELATORIO
# ==============================================================================
print("\n" + "=" * 78)
print("CORREÇÕES APLICADAS")
print("=" * 78)
for regra in ("R1", "R1-exceção", "R2", "R3a", "R3b", "R3c"):
    sub = df[df.regra == regra]
    if not len(sub):
        continue
    print(f"\n>> {regra}  ({len(sub)})")
    for _, r in sub.iterrows():
        print(f"   {str(r['nome'])[:54]:<54} -> {r['municipio_final']}")
        print(f"      {r['nota_decisao']}")

print("\n" + "-" * 78)
print("CONTAGEM FINAL POR MUNICÍPIO (CSV oficial de pontos de aferição)")
print("-" * 78)
csvj = df[df.fonte == "CSV pontos selecionados"]
print(f"  {'Município':<26} {'final':>6} {'declarado':>10} {'geométrico':>11}")
for cod, m in POR_CODIGO.items():
    fin = int((csvj.cod_municipio_final == cod).sum())
    dec = int((csvj.cod_declarado == cod).sum())
    geo = int((csvj.cod_ibge_geometrico == cod).sum())
    marca = "  <--" if not (fin == dec == geo) else ""
    print(f"  {m.nome_uf:<26} {fin:>6} {dec:>10} {geo:>11}{marca}")

# ==============================================================================
# 5. GRAVACAO
# ==============================================================================
saida = df.copy()
xlsx = DIR_DADOS / "pontos_municipio_corrigido.xlsx"
with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
    saida.to_excel(w, sheet_name="Pontos corrigidos", index=False)
    saida[saida.regra != ""].to_excel(w, sheet_name="Decisões", index=False)

g = gpd.GeoDataFrame(
    saida,
    geometry=[Point(xy) for xy in zip(saida.lon_final, saida.lat_final)],
    crs="EPSG:4674")
g.to_file(DIR_DADOS / "pontos_municipio_corrigido.geojson", driver="GeoJSON")

print(f"\nPlanilha: {xlsx}")
print(f"Camada:   {DIR_DADOS / 'pontos_municipio_corrigido.geojson'}")
