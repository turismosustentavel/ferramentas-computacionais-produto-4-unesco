# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
BASES CARTOGRAFICAS OFICIAIS
================================================================================
Carrega, com cache em memoria, as malhas oficiais usadas nas operacoes
espaciais: municipios, UF e pais (IBGE 2025), malha rodoviaria federal
(DNIT/SNV) e estadual (DNIT/CIDE) e zoneamento do reservatorio de Itaipu.

Todas as camadas sao devolvidas em SIRGAS 2000 / Brazil Polyconic
(EPSG:5880), projecao metrica usada nas medidas de distancia e area.

ENTRADAS (relativas a P4_DADOS, ver docs/mapa_de_dados.md)
    Levantamentos e Análises/Produto 4/01_Bases_Secundarias_Oficiais/Shapes/
        BR_Municipios_2025.zip, BR_UF_2025.zip, BR_Pais_2025.zip
    Entregas/Produto 4/produção/02_malha_rodoviaria_nacional_dnit_snv_shp/vw_snv_rod.shp
    Entregas/Produto 4/produção/03_malha_rodoviaria_pavimentacao_dnit_cide_shp/vw_cide_rod_2021.shp
    Levantamentos e Análises/Produto 4/08_Infraestrutura_e_Turismo_Nautico/
        01_Vetores_e_Rotas_Nauticas/Zoneamento_Altimetria/Zoneamento_FP_Reserv.shp
================================================================================
"""
from __future__ import annotations

import warnings

import geopandas as gpd

from comum import ACERVO, PRODUCAO, CRS_MAPA

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

_bases: dict[str, gpd.GeoDataFrame] = {}


def _zip(nome: str) -> str:
    return "/vsizip/" + str(SHAPES / nome).replace("\\", "/")


def municipios() -> gpd.GeoDataFrame:
    if "mun" not in _bases:
        g = gpd.read_file(_zip("BR_Municipios_2025.zip"))
        g["CD_MUN"] = g["CD_MUN"].astype(int)
        _bases["mun"] = g.to_crs(CRS_MAPA)
    return _bases["mun"]


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
    """Zoneamento oficial do reservatório de Itaipu (Zoneamento_FP_Reserv.shp),
    com o tipo de cada feição no campo `tipo`.

    None quando a camada não existe ou não pode ser lida.
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
