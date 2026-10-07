# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
BASES CARTOGRAFICAS OFICIAIS
================================================================================
Carrega, com cache em memoria, as malhas oficiais usadas nas operacoes
espaciais: municipios, UF e pais (IBGE 2025), municipios da faixa de fronteira
(IBGE 2024), faixa de 150 km e area de articulacao de 300 km, malha
rodoviaria federal (DNIT/SNV) e estadual (DNIT/CIDE), espelho d'agua do
reservatorio de Itaipu e hidrografia do OpenStreetMap.

Todas as camadas sao devolvidas em SIRGAS 2000 / Brazil Polyconic
(EPSG:5880), projecao metrica usada nas medidas de distancia e area.

ENTRADAS (relativas a P4_DADOS, ver docs/mapa_de_dados.md)
    Levantamentos e Análises/Produto 4/01_Bases_Secundarias_Oficiais/Shapes/
        BR_Municipios_2025.zip, BR_UF_2025.zip, BR_Pais_2025.zip,
        Municipios_da_Faixa_de_Fronteira_2024_shp.zip,
        Faixa_de_fronteira_150km.shp, Faixa_de_fronteira_300km.shp
    Entregas/Produto 4/produção/02_malha_rodoviaria_nacional_dnit_snv_shp/vw_snv_rod.shp
    Entregas/Produto 4/produção/03_malha_rodoviaria_pavimentacao_dnit_cide_shp/vw_cide_rod_2021.shp
    Levantamentos e Análises/Produto 4/08_Infraestrutura_e_Turismo_Nautico/
        01_Vetores_e_Rotas_Nauticas/Zoneamento_Altimetria/Zoneamento_FP_Reserv.shp

CACHE
    Levantamentos e Análises/Produto 4/09_Base_Socioeconomica_Municipal/
        06_Cartografia_Tematica/cache/agua_<recorte>.geojson  (Overpass API)
================================================================================
"""
from __future__ import annotations

import json
import warnings

import geopandas as gpd

from comum import ACERVO, PRODUCAO, CRS_MAPA, CRS_DADOS

warnings.filterwarnings("ignore", message=".*geographic CRS.*")
warnings.filterwarnings("ignore", category=UserWarning, module="pyogrio")

# O SNV atrasa em relacao ao chao. Trechos cuja condicao real foi verificada
# em campo entram aqui, por codigo SNV, com a superficie correta. Sem isto a
# Perimetral Leste de Foz - em operacao, pavimentada - seria classificada como
# via implantada sem pavimento (o SNV 202607A a traz como IMP / em obras).
CORRECOES_SNV = {
    "277APR5005": "PAV",   # Perimetral Leste: acesso norte -> BR-277/469/Av. das Cataratas
    "469BPR0010": "PAV",   # mesmo trecho, codificado tambem como BR-469
    "277APR5015": "PAV",   # Perimetral Leste: acesso a Ponte Tancredo Neves -> Ponte da Integracao
}

# ══════════════════════════════════════════════════════════════════════════════
# BASES
# ══════════════════════════════════════════════════════════════════════════════
SHAPES = ACERVO / "01_Bases_Secundarias_Oficiais" / "Shapes"
CACHE = ACERVO / "09_Base_Socioeconomica_Municipal" / "06_Cartografia_Tematica" / "cache"

_bases: dict[str, gpd.GeoDataFrame] = {}


def _zip(nome: str) -> str:
    return "/vsizip/" + str(SHAPES / nome).replace("\\", "/")


def municipios() -> gpd.GeoDataFrame:
    if "mun" not in _bases:
        g = gpd.read_file(_zip("BR_Municipios_2025.zip"))
        g["CD_MUN"] = g["CD_MUN"].astype(int)
        _bases["mun"] = g.to_crs(CRS_MAPA)
    return _bases["mun"]


def faixa(km: int = 150) -> gpd.GeoDataFrame | None:
    """Faixa de fronteira de 150 km ou área de articulação estendida de 300 km.

    A de 300 km engloba integralmente a de 150 km. Não é a faixa legal; é
    recorte analítico do estudo, para incorporar polos regionais além dos
    150 km.
    """
    chave = f"faixa{km}"
    if chave not in _bases:
        p = SHAPES / f"Faixa_de_fronteira_{km}km.shp"
        _bases[chave] = gpd.read_file(p).to_crs(CRS_MAPA) if p.exists() else None
    return _bases[chave]


def municipios_da_faixa() -> gpd.GeoDataFrame:
    """Municípios que compõem a faixa de fronteira (IBGE 2024)."""
    if "mun_faixa" not in _bases:
        g = gpd.read_file(_zip("Municipios_da_Faixa_de_Fronteira_2024_shp.zip"))
        _bases["mun_faixa"] = g.to_crs(CRS_MAPA)
    return _bases["mun_faixa"]


def ufs() -> gpd.GeoDataFrame:
    if "uf" not in _bases:
        _bases["uf"] = gpd.read_file(_zip("BR_UF_2025.zip")).to_crs(CRS_MAPA)
    return _bases["uf"]


def pais() -> gpd.GeoDataFrame:
    if "pais" not in _bases:
        _bases["pais"] = gpd.read_file(_zip("BR_Pais_2025.zip")).to_crs(CRS_MAPA)
    return _bases["pais"]


def rodovias(tipo: str = "federal") -> gpd.GeoDataFrame:
    """Malha do SNV (federal) ou CIDE (estadual), em EPSG:5880."""
    chave = f"rod_{tipo}"
    if chave not in _bases:
        if tipo == "federal":
            p = (PRODUCAO / "02_malha_rodoviaria_nacional_dnit_snv_shp" /
                 "vw_snv_rod.shp")
        else:
            p = (PRODUCAO / "03_malha_rodoviaria_pavimentacao_dnit_cide_shp" /
                 "vw_cide_rod_2021.shp")
        g = gpd.read_file(p).to_crs(CRS_MAPA)
        if tipo == "federal":
            for cod, sup in CORRECOES_SNV.items():
                g.loc[g["Codigo_SNV"] == cod, "Superficie"] = sup
        _bases[chave] = g
    return _bases[chave]


def reservatorio_itaipu() -> gpd.GeoDataFrame | None:
    """Espelho d'água do reservatório de Itaipu, do zoneamento oficial.

    Nos municípios lindeiros o lago é a feição de água dominante e o OSM nem
    sempre o traz como polígono único. Esta camada garante a massa d'água.
    """
    if "itaipu" not in _bases:
        p = (ACERVO / "08_Infraestrutura_e_Turismo_Nautico" /
             "01_Vetores_e_Rotas_Nauticas" / "Zoneamento_Altimetria" /
             "Zoneamento_FP_Reserv.shp")
        if not p.exists():
            _bases["itaipu"] = None
        else:
            try:
                _bases["itaipu"] = gpd.read_file(p).to_crs(CRS_MAPA)
            except Exception:
                _bases["itaipu"] = None
    return _bases["itaipu"]


def hidrografia(envelope_wgs84, nome_cache: str) -> gpd.GeoDataFrame | None:
    """Água do OpenStreetMap para o recorte, com cache local em GeoJSON.

    Busca na Overpass API os corpos d'água e cursos principais do envelope.
    O cache evita depender da rede a cada execução e mantém o resultado
    reproduzível. `envelope_wgs84` = (min_lon, min_lat, max_lon, max_lat).
    """
    arq = CACHE / f"agua_{nome_cache}.geojson"
    if arq.exists():
        try:
            g = gpd.read_file(arq)
            return g.to_crs(CRS_MAPA) if len(g) else None
        except Exception:
            return None

    import urllib.parse
    import urllib.request
    x0, y0, x1, y1 = envelope_wgs84
    bbox = f"{y0},{x0},{y1},{x1}"
    consulta = f"""
    [out:json][timeout:180];
    (
      way["natural"="water"]({bbox});
      relation["natural"="water"]({bbox});
      way["waterway"="riverbank"]({bbox});
      way["waterway"="river"]({bbox});
availability
    );
    out geom;
    """.replace("availability\n", "")
    try:
        req = urllib.request.Request(
            "https://overpass-api.de/api/interpreter",
            data=urllib.parse.urlencode({"data": consulta}).encode(),
            headers={"User-Agent": "ItaipuParquetec-Produto4/1.0"})
        bruto = json.loads(urllib.request.urlopen(req, timeout=240).read())
    except Exception as e:
        print(f"     [aviso] hidrografia OSM indisponível ({str(e)[:50]})")
        return None

    from shapely.geometry import LineString, Polygon
    feicoes = []
    for el in bruto.get("elements", []):
        pts = [(p["lon"], p["lat"]) for p in (el.get("geometry") or [])]
        if len(pts) < 2:
            continue
        fechado = pts[0] == pts[-1] and len(pts) >= 4
        geom = Polygon(pts) if fechado else LineString(pts)
        feicoes.append({"tipo": "poligono" if fechado else "linha",
                        "geometry": geom})
    if not feicoes:
        return None
    g = gpd.GeoDataFrame(feicoes, crs=CRS_DADOS)
    CACHE.mkdir(parents=True, exist_ok=True)
    g.to_file(arq, driver="GeoJSON")
    return g.to_crs(CRS_MAPA)
