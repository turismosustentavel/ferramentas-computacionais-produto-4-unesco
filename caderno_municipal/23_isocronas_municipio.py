# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
ISOCRONAS RODOVIARIAS A PARTIR DO MUNICIPIO
================================================================================
Tempo de viagem por estrada a partir do centro do municipio, no mesmo metodo
das isocronas regionais do Produto 4 (a modelagem regional nao esta neste
repositorio). Calcula:

    - o tempo de cada via da malha principal a partir da origem e a faixa de
      tempo em que ela cai (ate 8 h);
    - o tempo ate os demais municipios do estudo, ate as cidades fronteiricas
      do outro lado da linha e ate cidades de referencia da regiao;
    - a extensao de via alcancada em cada faixa.

METODO
    origem      ponto de convergencia dos trajetos modelados entre os
                atrativos e o centro da area das Atividades Caracteristicas
                do Turismo (ACTs) do municipio
                (fluxos_p4.centro_da_modelagem); sem trajetos, um ponto
                interior do poligono municipal (IBGE)
    malha       OpenStreetMap, vias motorway | trunk | primary | secondary
                (e respectivos _link), dos dois lados da fronteira, numa
                caixa de +-5 graus de latitude e +-6 graus de longitude em
                torno da origem, baixada em blocos de 2,5 graus pela Overpass
                API; os blocos sao unidos pelo id do OSM
    custo       comprimento (Haversine) / velocidade, em horas
    grafo       nao direcionado; trecho repetido fica com o menor tempo em
                circulacao
    roteamento  Dijkstra de fonte unica a partir do no mais proximo da
                origem, com corte em 14 h
    via         tempo do trecho = menor tempo entre seus nos
    faixas      pelo tempo lento: ate 1 h, 1 a 2, 2 a 3, 3 a 4, 4 a 5,
                5 a 6 e 6 a 8 h; vias alem de 8 h ficam fora
    destino     no da malha mais proximo do ponto, se a ate 15 km; o trecho
                ate a via entra a 40 km/h nos dois tempos. Acima de 15 km, ou
                sem rota a partir da origem, o tempo fica vazio. Cada
                municipio do estudo e representado pelo seu proprio centro da
                modelagem de ACTs, o mesmo criterio da origem

O TEMPO E UM INTERVALO, NAO UM NUMERO
    O limite sinalizado e a velocidade que a via permite no melhor caso; a
    velocidade de circulacao e a que o percurso rende de fato, descontando
    travessias urbanas, intersecoes, curvas, caminhoes, radares e as paradas
    inevitaveis. Entre uma e outra ha meia hora de diferenca em duas horas de
    viagem, e nenhuma das duas e "a" resposta.

    Por isso o Dijkstra roda DUAS VEZES sobre o mesmo grafo, com dois pesos:

        rapido   limite sinalizado (maxspeed, aceito entre 1 e 120 km/h) ou o
                 padrao da classe
                 motorway 100, trunk 80, primary 70, secondary 60, alcas 50
        lento    velocidade media de circulacao da classe, limitada pelo
                 limite sinalizado quando este for menor
                 motorway 90, trunk 70, primary 60, secondary 50, alcas 40

    O resultado e o intervalo [rapido, lento], em horas. As faixas usam o
    tempo LENTO, o conservador para planejamento.

Travessia de fronteira e filas de aduana ficam fora do custo: o tempo e de
percurso, nao de espera.

ENTRADAS (caminhos relativos a P4_DADOS; ver comum.py)
    Levantamentos e Análises/Produto 4/01_Bases_Secundarias_Oficiais/Shapes/
        BR_Municipios_2025.zip
            malha municipal do IBGE (2025), lida por bases_p4.municipios()
    Entregas/Produto 4/produção/Seleção dos pontos para aferição/final/
        z_rotas_tomtom/tomtom_routes.csv
            trajetos da modelagem de ACTs (TomTom Routing API), lidos por
            fluxos_p4.centro_da_modelagem() para fixar origem e destinos
    OpenStreetMap, pela Overpass API (rede necessaria so na primeira
    execucao de cada municipio; depois vale o cache abaixo)
    comum.MUNICIPIOS e comum.FRONTEIRICAS; REFERENCIAS, neste arquivo

CACHE
    Entregas/Produto 4/produção/Caderno de informações por município/
        02_Dados_Municipais/cache/osm_isocronas_<slug>/bloco_<lat>_<lon>.json
    Resposta da Overpass, um arquivo por bloco. Bloco presente no cache nao
    e baixado de novo.

SAIDAS
    Entregas/Produto 4/produção/Caderno de informações por município/
        02_Dados_Municipais/isocronas/<slug>/
    isocronas_<slug>.geojson
        vias alcancadas em ate 8 h, EPSG:4674. Atributos: tempo_h (lento),
        tempo_h_rapido, tipo (classe highway do OSM), nome, faixa (limite
        superior da faixa, em horas: 1, 2, 3, 4, 5, 6 ou 8)
    tempos_<slug>.csv
        um registro por destino: grupo (municipio do estudo, cidade
        fronteirica, cidade de referencia), lon, lat, tempo_h_rapido,
        tempo_h_lento
    metricas_isocronas_<slug>.json
        origem, metodo, velocidades, tempos [rapido, lento] por destino e
        km de via por faixa

COMO EXECUTAR
    python 23_isocronas_municipio.py 02_Medianeira_PR
    python 23_isocronas_municipio.py 02_Medianeira_PR 06_Guaira_PR

    O argumento e o slug de comum.MUNICIPIOS (um ou mais). Sem cache, o
    download da malha leva de minutos a dezenas de minutos por municipio.
================================================================================
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import requests
from shapely.geometry import LineString

sys.path.insert(0, str(Path(__file__).parent))
import bases_p4 as bp                                            # noqa: E402
import fluxos_p4 as fx                                           # noqa: E402
from comum import (CRS_DADOS, CRS_MAPA, DIR_DADOS,               # noqa: E402
                   FRONTEIRICAS, MUNICIPIOS, POR_SLUG)

DIR_CACHE = DIR_DADOS / "cache"
DIR_SAIDA = DIR_DADOS / "isocronas"

# ══════════════════════════════════════════════════════════════════════════════
# PARAMETROS
# ══════════════════════════════════════════════════════════════════════════════
# Faixas das isocronas regionais: (limite superior em horas, rotulo)
FAIXAS = [(1, "Até 1 h"), (2, "1 a 2 h"), (3, "2 a 3 h"), (4, "3 a 4 h"),
          (5, "4 a 5 h"), (6, "5 a 6 h"), (8, "6 a 8 h")]
T_MAX = 8                 # h: vias alem disso ficam fora das faixas
# Corte folgado do Dijkstra: as cidades de referencia alem de 8 h tambem
# recebem tempo, embora fiquem fora das faixas.
T_CORTE = 14              # h

# km/h. LIMITE = o que a via permite; CIRCULACAO = o que o percurso rende.
LIMITE = {"motorway": 100, "trunk": 80, "primary": 70, "secondary": 60}
CIRCULACAO = {"motorway": 90, "trunk": 70, "primary": 60, "secondary": 50}
LIMITE_LINK, CIRCULACAO_LINK = 50, 40             # alcas e acessos

# Ligacao do destino a malha: no mais proximo ate esta distancia, percorrida
# a esta velocidade nos dois tempos.
ACESSO_MAX_M = 15000
V_ACESSO_KMH = 40

# 8 h a ~80 km/h: raio de ~600 km. A caixa das isocronas regionais (3 x 4,5
# graus) e ampliada para nao cortar as rodovias rapidas. Uma consulta unica
# desse tamanho estoura o tempo do Overpass: a caixa e baixada em blocos de
# 2,5 graus, cada um com cache proprio, e os blocos sao unidos pelo id do OSM.
PASSO = 2.5               # graus
MEIA_ALTURA = 5.0         # graus de latitude para cada lado da origem
MEIA_LARGURA = 6.0        # graus de longitude para cada lado da origem

OVERPASS = ["https://overpass-api.de/api/interpreter",
            "https://lz4.overpass-api.de/api/interpreter",
            "https://z.overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter"]

# Cidades de referencia (lon, lat do centro urbano). O ponto interior do
# poligono municipal nao serve: num municipio grande ele cai longe da cidade.
REFERENCIAS = {
    "Cascavel": (-53.4552, -24.9555), "Toledo": (-53.7430, -24.7246),
    "Curitiba": (-49.2733, -25.4284), "Londrina": (-51.1696, -23.3045),
    "Maringá": (-51.9333, -23.4205), "Florianópolis": (-48.5480, -27.5954),
    "Chapecó": (-52.6152, -27.1004), "Campo Grande": (-54.6201, -20.4697),
    "Dourados": (-54.8056, -22.2211),
    "Asunción (PY)": (-57.5759, -25.2637),
    "Encarnación (PY)": (-55.8667, -27.3306),
    "Posadas (AR)": (-55.8961, -27.3671),
}

METODO = ("OSM motorway/trunk/primary/secondary; Dijkstra duas vezes sobre o "
          "mesmo grafo — no limite sinalizado e na velocidade média de "
          "circulação da classe. Os tempos são intervalos [rápido, lento], em "
          "horas; as faixas usam o tempo lento. Tempo de percurso, sem espera "
          "em aduana.")

GRUPOS = (("municipio_estudo", "tempo_h_municipios_estudo"),
          ("cidade_fronteirica", "tempo_h_cidades_fronteiricas"),
          ("cidade_referencia", "tempo_h_ate"))


# ══════════════════════════════════════════════════════════════════════════════
# VELOCIDADES E DISTANCIAS
# ══════════════════════════════════════════════════════════════════════════════
def haversine(lat1, lon1, lat2, lon2):
    """Distancia em metros sobre a esfera de raio 6.371 km."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _maxspeed(maxspeed):
    """Valor numerico do maxspeed do OSM, aceito entre 1 e 120 km/h."""
    if maxspeed:
        dig = "".join(c for c in str(maxspeed) if c.isdigit())
        if dig and 0 < int(dig) <= 120:
            return int(dig)
    return None


def velocidades(tipo, maxspeed) -> tuple[int, int]:
    """(limite, circulação) em km/h para o trecho.

    O limite sinalizado entra como valor no primeiro caso e como teto no
    segundo: uma travessia urbana com maxspeed 40 não se percorre a 60, mas
    uma pista dupla com limite 110 tampouco rende 110 de média.
    """
    ms = _maxspeed(maxspeed)
    link = tipo.endswith("_link")
    lim = ms or (LIMITE_LINK if link else LIMITE.get(tipo, 50))
    circ = CIRCULACAO_LINK if link else CIRCULACAO.get(tipo, 45)
    if ms:
        circ = min(circ, ms)
    return lim, max(circ, 1)


def faixa_de(t):
    """Limite superior, em horas, da faixa em que cai o tempo `t`."""
    for lim, _rot in FAIXAS:
        if t <= lim:
            return lim
    return None


# ══════════════════════════════════════════════════════════════════════════════
# MALHA (OVERPASS, COM CACHE POR BLOCO)
# ══════════════════════════════════════════════════════════════════════════════
def baixar(bbox):
    """Vias principais do OSM na caixa (sul, oeste, norte, leste)."""
    s, w, n, e = bbox
    q = f"""[out:json][timeout:180];
    (way["highway"~"^(motorway|trunk|primary|secondary)(_link)?$"]({s},{w},{n},{e}););
    out body; >; out skel qt;"""
    # Os espelhos do Overpass saturam: em quarenta minutos de download uma
    # saturação de dois minutos é banal, e desistir dela jogava fora os
    # dezesseis blocos já baixados. A espera cresce até dez minutos, que é
    # a ordem de grandeza em que um espelho volta.
    for tentativa in range(8):
        for url in OVERPASS:
            try:
                print(f"   Overpass: {url}", flush=True)
                r = requests.post(url, data={"data": q}, timeout=200,
                                  headers={"User-Agent": "CadernoP4/1.0"})
                if r.status_code == 200:
                    dados = r.json()
                    if isinstance(dados.get("elements"), list):
                        print(f"      {len(dados['elements'])} elementos",
                              flush=True)
                        return dados
                print(f"      HTTP {r.status_code}: {r.text[:120]!r}",
                      flush=True)
            except Exception as ex:                          # noqa: BLE001
                print(f"      falha: {ex}", flush=True)
        espera = min(30 * 2 ** tentativa, 600)
        print(f"   espelhos saturados; nova tentativa em {espera}s",
              flush=True)
        time.sleep(espera)
    raise RuntimeError("Overpass indisponível: malha não baixada")


def blocos(lat0: float, lon0: float) -> list[tuple]:
    """Blocos (sul, oeste, norte, leste) da caixa em torno da origem."""
    lat_a, lat_b = lat0 - MEIA_ALTURA, lat0 + MEIA_ALTURA
    lon_a, lon_b = lon0 - MEIA_LARGURA, lon0 + MEIA_LARGURA
    return [(s, w, min(s + PASSO, lat_b), min(w + PASSO, lon_b))
            for s in np.arange(lat_a, lat_b, PASSO)
            for w in np.arange(lon_a, lon_b, PASSO)]


def dir_cache(slug: str) -> Path:
    return DIR_CACHE / f"osm_isocronas_{slug}"


def carregar_malha(slug: str, lat0: float, lon0: float):
    """Nós {id: (lat, lon)} e lista de vias (elementos 'way' do OSM).

    Cada bloco é lido do cache ou baixado e gravado nele. Vias e nós que
    aparecem em mais de um bloco são unidos pelo id do OSM.
    """
    pasta = dir_cache(slug)
    pasta.mkdir(parents=True, exist_ok=True)
    caixas = blocos(lat0, lon0)
    nos, vias_por_id = {}, {}
    for i, (s, w, n, e) in enumerate(caixas, 1):
        arq = pasta / f"bloco_{s:.2f}_{w:.2f}.json"
        if arq.exists():
            dados = json.loads(arq.read_text("utf-8"))
        else:
            print(f"Bloco {i}/{len(caixas)}: {s:.1f}, {w:.1f}")
            dados = baixar((s, w, n, e))
            arq.write_text(json.dumps(dados), "utf-8")
            time.sleep(3)
        for el in dados["elements"]:
            if el["type"] == "node":
                nos[el["id"]] = (el["lat"], el["lon"])
            elif el["type"] == "way":
                vias_por_id[el["id"]] = el
    vias = list(vias_por_id.values())
    print(f"Malha: {len(vias)} vias, {len(nos)} nós")
    return nos, vias


# ══════════════════════════════════════════════════════════════════════════════
# GRAFO E ROTEAMENTO
# ══════════════════════════════════════════════════════════════════════════════
def montar_grafo(nos: dict, vias: list) -> nx.Graph:
    """Um grafo, dois pesos: o mesmo percurso no limite e em circulação."""
    G = nx.Graph()
    for w in vias:
        t = w.get("tags", {})
        v_lim, v_circ = velocidades(t.get("highway", ""), t.get("maxspeed"))
        ns = [n for n in w.get("nodes", []) if n in nos]
        for a, b in zip(ns[:-1], ns[1:]):
            d = haversine(*nos[a], *nos[b])
            h_rap, h_len = d / (v_lim * 1000.0), d / (v_circ * 1000.0)
            if not G.has_edge(a, b) or G[a][b]["lento"] > h_len:
                G.add_edge(a, b, rapido=h_rap, lento=h_len)
    return G


class Acessibilidade:
    """Tempos de viagem a partir da origem, sobre o grafo da malha.

    `lento` e `rapido` são {nó: horas} para os nós alcançados até T_CORTE.
    """

    def __init__(self, G: nx.Graph, nos: dict, lat0: float, lon0: float):
        self.ids = np.array([n for n in G.nodes])
        self.coords = np.array([nos[n] for n in self.ids])
        self.origem, self.acoplamento_m = self.no_mais_proximo(lat0, lon0)
        print(f"Nó de origem a {self.acoplamento_m:.0f} m do centro")
        self.lento = nx.single_source_dijkstra_path_length(
            G, self.origem, weight="lento", cutoff=T_CORTE)
        self.rapido = nx.single_source_dijkstra_path_length(
            G, self.origem, weight="rapido", cutoff=T_CORTE)
        print(f"Nós alcançados: {len(self.lento)}")

    def no_mais_proximo(self, lat, lon):
        """(id do nó, distância em metros) do nó do grafo mais próximo."""
        d = (self.coords[:, 0] - lat) ** 2 + (
            (self.coords[:, 1] - lon) * math.cos(math.radians(lat))) ** 2
        i = int(np.argmin(d))
        return self.ids[i], haversine(lat, lon, *self.coords[i])

    def tempo_ate(self, lon, lat):
        """[rápido, lento] em horas, ou None se o ponto não se conecta à malha."""
        n, d = self.no_mais_proximo(lat, lon)
        if n not in self.lento or d > ACESSO_MAX_M:
            return None
        acesso = d / (V_ACESSO_KMH * 1000.0)
        return [round(self.rapido.get(n, self.lento[n]) + acesso, 2),
                round(self.lento[n] + acesso, 2)]


def vias_alcancadas(nos: dict, vias: list,
                    acc: Acessibilidade) -> gpd.GeoDataFrame:
    """Vias alcançadas em até T_MAX, com tempo e faixa, em EPSG:5880."""
    linhas, meta = [], []
    for w in vias:
        ns = [n for n in w.get("nodes", []) if n in nos]
        ts = [acc.lento[n] for n in ns if n in acc.lento]
        if len(ns) < 2 or not ts:
            continue
        t = min(ts)
        if t > T_MAX:
            continue
        tr = [acc.rapido[n] for n in ns if n in acc.rapido]
        linhas.append(LineString([(nos[n][1], nos[n][0]) for n in ns]))
        meta.append({"tempo_h": t, "tempo_h_rapido": min(tr) if tr else t,
                     "tipo": w.get("tags", {}).get("highway", ""),
                     "nome": w.get("tags", {}).get("name", "")})
    gdf = gpd.GeoDataFrame(meta, geometry=linhas, crs=4326).to_crs(CRS_MAPA)
    gdf["faixa"] = gdf.tempo_h.map(faixa_de)
    print(f"Vias alcançadas em até {T_MAX} h: {len(gdf)}")
    return gdf


# ══════════════════════════════════════════════════════════════════════════════
# ORIGEM E DESTINOS
# ══════════════════════════════════════════════════════════════════════════════
def origem(m, mun: gpd.GeoDataFrame):
    """Origem em EPSG:5880 e (lat, lon) em graus."""
    o_mapa = fx.centro_da_modelagem(m.nome)
    if o_mapa is None:
        alvo = mun[mun.CD_MUN == m.codigo_ibge]
        o_mapa = alvo.geometry.iloc[0].representative_point()
    o = gpd.GeoSeries([o_mapa], crs=CRS_MAPA).to_crs(4326).iloc[0]
    return o_mapa, o.y, o.x


def tempos_destinos(m, mun: gpd.GeoDataFrame, acc: Acessibilidade):
    """Tempos até as cidades de referência, as fronteiriças e os municípios
    do estudo; devolve também as coordenadas usadas para estes últimos."""
    refs = {nome: acc.tempo_ate(*xy) for nome, xy in REFERENCIAS.items()}
    front = {nome: acc.tempo_ate(lon, lat)
             for nome, lon, lat, _ in FRONTEIRICAS}
    estudo, coord_estudo = {}, {}
    for outro in MUNICIPIOS:
        if outro.slug == m.slug:
            continue
        g = mun[mun.CD_MUN == outro.codigo_ibge]
        if not len(g):
            continue
        # Destino: o centro da oferta turística do outro município, o mesmo
        # ponto que é origem quando ele é o analisado. Um ponto interior do
        # polígono cai longe da cidade nos municípios de território grande ou
        # recortado e distorce o tempo entre cidades gêmeas.
        c = fx.centro_da_modelagem(outro.nome)
        if c is None:
            c = g.geometry.iloc[0].representative_point()
        p = gpd.GeoSeries([c], crs=CRS_MAPA).to_crs(4326).iloc[0]
        estudo[outro.nome] = acc.tempo_ate(p.x, p.y)
        coord_estudo[outro.nome] = (p.x, p.y)
    return refs, front, estudo, coord_estudo


def _chave_ordem(kv):
    """Conectados primeiro, do mais perto ao mais longe (tempo lento)."""
    v = kv[1]
    return (v is None, v[1] if v else 0)


def metricas(lat0, lon0, gdf, refs, front, estudo) -> dict:
    """Registro do cálculo: origem, parâmetros, tempos e km por faixa."""
    ext_km = {rot: round(float(gdf[gdf.faixa == lim].length.sum() / 1000))
              for lim, rot in FAIXAS}
    return {
        "origem_lat_lon": [round(lat0, 5), round(lon0, 5)],
        "metodo": METODO,
        "velocidades_km_h": {
            "limite": {**LIMITE, "alças (_link)": LIMITE_LINK},
            "circulação": {**CIRCULACAO, "alças (_link)": CIRCULACAO_LINK}},
        "tempo_h_ate": dict(sorted(refs.items(), key=_chave_ordem)),
        "tempo_h_municipios_estudo": dict(sorted(estudo.items(),
                                                 key=_chave_ordem)),
        "tempo_h_cidades_fronteiricas": dict(sorted(front.items(),
                                                    key=_chave_ordem)),
        "km_de_via_por_faixa": ext_km,
    }


def tabela_tempos(met: dict, coord_estudo: dict) -> pd.DataFrame:
    """Um registro por destino, na ordem das métricas."""
    coords = {"municipio_estudo": coord_estudo,
              "cidade_fronteirica": {n: (lon, lat)
                                     for n, lon, lat, _ in FRONTEIRICAS},
              "cidade_referencia": REFERENCIAS}
    linhas = []
    for grupo, chave in GRUPOS:
        for nome, t in met[chave].items():
            lon, lat = coords[grupo][nome]
            linhas.append({"grupo": grupo, "destino": nome,
                           "lon": lon, "lat": lat,
                           "tempo_h_rapido": t[0] if t else None,
                           "tempo_h_lento": t[1] if t else None})
    return pd.DataFrame(linhas)


# ══════════════════════════════════════════════════════════════════════════════
# EXECUCAO
# ══════════════════════════════════════════════════════════════════════════════
def isocronas(m, mun: gpd.GeoDataFrame | None = None) -> dict:
    """Todo o cálculo para um município; nada é gravado além do cache."""
    if mun is None:
        mun = bp.municipios()
    o_mapa, lat0, lon0 = origem(m, mun)
    print(f"Origem: {lat0:.5f}, {lon0:.5f}")
    nos, vias = carregar_malha(m.slug, lat0, lon0)
    G = montar_grafo(nos, vias)
    acc = Acessibilidade(G, nos, lat0, lon0)
    gdf = vias_alcancadas(nos, vias, acc)
    refs, front, estudo, coord_estudo = tempos_destinos(m, mun, acc)
    met = metricas(lat0, lon0, gdf, refs, front, estudo)
    return {"origem": o_mapa, "lat0": lat0, "lon0": lon0, "acc": acc,
            "vias": gdf, "refs": refs, "front": front, "estudo": estudo,
            "coord_estudo": coord_estudo, "metricas": met,
            "tempos": tabela_tempos(met, coord_estudo)}


def gravar(m, res: dict) -> list[Path]:
    """Grava as vias (GeoJSON, EPSG:4674), os tempos (CSV) e as métricas."""
    saida = DIR_SAIDA / m.slug
    saida.mkdir(parents=True, exist_ok=True)
    arq_vias = saida / f"isocronas_{m.slug}.geojson"
    arq_tempos = saida / f"tempos_{m.slug}.csv"
    arq_met = saida / f"metricas_isocronas_{m.slug}.json"
    if arq_vias.exists():
        arq_vias.unlink()
    res["vias"][["tempo_h", "tempo_h_rapido", "tipo", "nome", "faixa",
                 "geometry"]].to_crs(CRS_DADOS).to_file(arq_vias,
                                                        driver="GeoJSON")
    res["tempos"].to_csv(arq_tempos, index=False, encoding="utf-8-sig")
    arq_met.write_text(json.dumps(res["metricas"], ensure_ascii=False,
                                  indent=1), "utf-8")
    return [arq_vias, arq_tempos, arq_met]


def main(argv: list[str] | None = None) -> None:
    args = [a for a in (sys.argv[1:] if argv is None else argv)
            if not a.startswith("--")]
    if not args:
        print("Informe o slug do município. Ex.: 01_Foz_do_Iguacu_PR")
        sys.exit(1)
    desconhecidos = [a for a in args if a not in POR_SLUG]
    if desconhecidos:
        print("Slug não reconhecido: " + ", ".join(desconhecidos))
        print("Válidos: " + ", ".join(m.slug for m in MUNICIPIOS))
        sys.exit(1)
    mun = bp.municipios()
    for slug in args:
        m = POR_SLUG[slug]
        print(f"\n{m.nome_uf}")
        res = isocronas(m, mun)
        print(json.dumps(res["metricas"], ensure_ascii=False, indent=1))
        for p in gravar(m, res):
            print("   " + str(p))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
