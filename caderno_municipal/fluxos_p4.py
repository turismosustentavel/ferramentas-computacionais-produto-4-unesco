# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
TRAJETOS, SOBREPOSICAO DE FLUXOS E PONTOS SELECIONADOS
================================================================================
Reproduz, a partir das saidas da selecao dos pontos de afericao
(`selecao_pontos/selecao_pontos_afericao.py`), os trajetos e os agrupamentos:

    1. Pares origem-destino: cada atrativo do municipio ligado ao centro da
       mancha de Atividades Caracteristicas do Turismo.
    2. Roteamento pela TomTom Routing API sobre a malha viaria real; de cada
       rota extraem-se os vertices (waypoints).
    3. Agrupamento dos waypoints por DBSCAN, metrica haversine, raio de 100 m,
       min_samples=1. A FREQUENCIA de cada agrupamento e a CONTAGEM DE
       WAYPOINTS que caem nele. Retem-se os 100 maiores por municipio.

FREQUENCIA E SOBREPOSICAO DE TRAJETOS
    A frequencia registrada na camada `2_pontos_sobreposicao_fluxos` NAO e o
    numero de trajetos que passam pelo ponto: e a densidade de vertices das
    rotas ali. A densidade de vertices cresce onde a geometria viaria e
    complexa, nao necessariamente onde ha mais sobreposicao, e as duas medidas
    podem divergir.

    Este modulo devolve as duas: `freq`, que reproduz a camada de selecao
    waypoint a waypoint, e `rotas_distintas`, que e a sobreposicao de
    trajetos propriamente dita.

ENTRADAS (relativas a P4_DADOS)
    Entregas/Produto 4/produção/Seleção dos pontos para aferição/
        final/z_rotas_tomtom/tomtom_routes.csv  e demais saidas da selecao
    Levantamentos e Análises/Produto 4/06_Dados_Processados_Pipeline/
        CNPJs_e_Atrativos_Clusters/camadas_qgis/1_pontos_afericao_selecionados.geojson
================================================================================
"""
from __future__ import annotations

import json

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point
from sklearn.cluster import DBSCAN

from comum import CRS_DADOS, CRS_MAPA
from comum import CAMADAS_QGIS, PRODUCAO

SELECAO = PRODUCAO / "Seleção dos pontos para aferição"
ROTAS_CSV = SELECAO / "final" / "z_rotas_tomtom" / "tomtom_routes.csv"
SELECIONADOS = CAMADAS_QGIS / "1_pontos_afericao_selecionados.geojson"

EPS_METROS = 100          # raio do agrupamento, como na selecao dos pontos
TOP_N = 100               # agrupamentos retidos por municipio
RAIO_TERRA_M = 6_371_000

METODO = (
    "Os trajetos são calculados sobre a malha viária real pela API de "
    "roteamento da TomTom, ligando cada atrativo mapeado ao centro da mancha "
    "de Atividades Características do Turismo. De cada rota extraem-se os "
    "vértices que a descrevem, e esses vértices são agrupados por DBSCAN, com "
    "métrica haversine e raio de 100 metros. A frequência de cada agrupamento "
    "é a contagem de vértices que nele caem; retêm-se os cem agrupamentos de "
    "maior frequência em cada município."
)

_cache: dict = {}


def _vertices(nome_municipio: str) -> pd.DataFrame:
    if "rot" not in _cache:
        _cache["rot"] = pd.read_csv(ROTAS_CSV)
    d = _cache["rot"]
    return d[d.municipio.astype(str).str.strip() == nome_municipio].dropna(
        subset=["latitude", "longitude"]).copy()


def rotas(nome_municipio: str) -> gpd.GeoDataFrame:
    """Uma linha por trajeto, com o atrativo que liga e a extensão."""
    v = _vertices(nome_municipio)
    linhas, meta = [], []
    for rid, grupo in v.groupby("id", sort=False):
        if len(grupo) < 2:
            continue
        linhas.append(LineString(
            [(x, y) for x, y in zip(grupo.longitude, grupo.latitude)]))
        meta.append({"id": rid, "atrativo": grupo.nome.iloc[0],
                     "vertices": len(grupo)})
    if not linhas:
        return gpd.GeoDataFrame()
    g = gpd.GeoDataFrame(pd.DataFrame(meta), geometry=linhas,
                         crs=CRS_DADOS).to_crs(CRS_MAPA)
    g["extensao_km"] = g.length / 1000.0
    return g


def centro_da_modelagem(nome_municipio: str):
    """O ponto em que todos os trajetos do município convergem.

    É o centro da mancha de ACTs adotado na esteira de seleção — lido dos
    próprios trajetos, e não recalculado, para que toda medida parta da
    mesma origem que a modelagem usou.
    """
    v = _vertices(nome_municipio)
    if not len(v):
        return None
    fins = v.groupby("id").tail(1)
    p = fins.groupby(["latitude", "longitude"]).size().idxmax()
    return gpd.GeoSeries([Point(p[1], p[0])],
                         crs=CRS_DADOS).to_crs(CRS_MAPA).iloc[0]


def clusters(nome_municipio: str, excluir_ids=()) -> gpd.GeoDataFrame:
    """Agrupamentos de vértices: `freq` (camada publicada) e `rotas_distintas`.

    `excluir_ids`: rotas modeladas até um atrativo mal localizado (Guaíra,
    29/09/2026). Os agrupamentos e a `freq` ficam como publicados, porque
    foram a base da escolha dos pontos de campo; só a contagem de rotas
    distintas deixa de contar essas rotas, para o texto não dizer "26 dos 24
    trajetos".
    """
    v = _vertices(nome_municipio)
    if not len(v):
        return gpd.GeoDataFrame()
    rot = DBSCAN(eps=EPS_METROS / RAIO_TERRA_M, min_samples=1,
                 metric="haversine").fit_predict(
        np.radians(v[["latitude", "longitude"]].values))
    v["cl"] = rot
    validas = v[~v.id.isin(list(excluir_ids))].groupby("cl").id.nunique()
    g = (v.groupby("cl")
         .agg(freq=("cl", "size"),
              lat=("latitude", "mean"), lon=("longitude", "mean"))
         .assign(rotas_distintas=lambda d: validas.reindex(d.index)
                 .fillna(0).astype(int))
         .sort_values("freq", ascending=False).head(TOP_N)
         .reset_index(drop=True))
    g["rank"] = g.index + 1
    return gpd.GeoDataFrame(
        g, geometry=[Point(xy) for xy in zip(g.lon, g.lat)],
        crs=CRS_DADOS).to_crs(CRS_MAPA)


def selecionados(nome_municipio: str) -> gpd.GeoDataFrame:
    """Pontos escolhidos no painel de decisão, com a justificativa registrada."""
    if not SELECIONADOS.exists():
        return gpd.GeoDataFrame()
    dados = json.loads(SELECIONADOS.read_text("utf-8"))
    d = pd.DataFrame([f["properties"] for f in dados["features"]])
    d = d[d.MUNICIPIO.astype(str).str.contains(nome_municipio, na=False)]
    if not len(d):
        return gpd.GeoDataFrame()
    return gpd.GeoDataFrame(
        d, geometry=[Point(xy) for xy in zip(d.LONGITUDE, d.LATITUDE)],
        crs=CRS_DADOS).to_crs(CRS_MAPA).sort_values("ORDEM")


def justificativas(nome_municipio: str, pontos_campo: gpd.GeoDataFrame,
                   limite_m: float = 300.0) -> dict:
    """Liga cada justificativa do painel ao ponto de campo mais próximo.

    Os pontos do painel e os aferidos em campo não têm identificador comum: o
    vínculo é geométrico. Acima de `limite_m` não se assume correspondência.
    """
    sel = selecionados(nome_municipio)
    if not len(sel) or not len(pontos_campo):
        return {}
    alvo = pontos_campo.to_crs(CRS_MAPA)
    saida = {}
    for r in sel.itertuples():
        d = alvo.geometry.distance(r.geometry)
        i = d.idxmin()
        if d[i] <= limite_m:
            saida[alvo.at[i, "ordem"]] = {
                "justificativa": str(r.JUSTIFIC).strip(),
                "ordem_no_painel": int(r.ORDEM),
                "distancia_m": round(float(d[i])),
            }
    return saida
