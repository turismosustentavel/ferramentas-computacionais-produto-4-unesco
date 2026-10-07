# -*- coding: utf-8 -*-
"""
Contagem de trafego do DNIT e malha ferroviaria.

A malha rodoviaria diz por onde se chega; nao diz QUANTO passa por ali. O
Plano Nacional de Contagem de Trafego (DNIT) traz o volume medio diario anual
dos trechos do PR e do MS, e todos carregam o `Codigo_SNV`, a mesma chave da
malha do SNV: a juncao e direta.

Trecho sem contagem NAO e trecho de pouco movimento: significa "nao medido".

ENTRADAS (relativas a P4_DADOS)
    Levantamentos e Análises/Produto 4/05_Telemetria_e_BigData/DNIT_PNCT_Trafego/
        malha_fluxo_pnct_2025_oficial.geojson, malha_fluxo_veiculos_vdm.geojson
    Levantamentos e Análises/Produto 4/01_Bases_Secundarias_Oficiais/Shapes/
        vw_dif_ferrovias.zip
"""
from __future__ import annotations

import re
import unicodedata

import geopandas as gpd

from comum import ACERVO

PNCT = (ACERVO / "05_Telemetria_e_BigData" / "DNIT_PNCT_Trafego" /
        "malha_fluxo_pnct_2025_oficial.geojson")
VDM = (ACERVO / "05_Telemetria_e_BigData" / "DNIT_PNCT_Trafego" /
       "malha_fluxo_veiculos_vdm.geojson")
FERROVIAS = (ACERVO / "01_Bases_Secundarias_Oficiais" / "Shapes" /
             "vw_dif_ferrovias.zip")

_CACHE: dict = {}


def _ch(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore")
    return re.sub(r"[^a-z]", "", s.decode().lower())


def contagens() -> dict[str, dict]:
    """Código SNV → volume médio diário anual, total e comercial."""
    if "pnct" not in _CACHE:
        if not PNCT.exists():
            _CACHE["pnct"] = {}
        else:
            g = gpd.read_file(PNCT)
            _CACHE["pnct"] = {
                str(r.Codigo_SNV): {
                    "vmda": float(r.VMDa_Total or 0),
                    "comercial": float(r.VMDa_C or 0),
                    "classe": str(r.classe_vmd),
                    "br": int(r.vl_br) if r.vl_br else None,
                    "de": str(r.Local_Inic), "ate": str(r.Local_Fim),
                }
                for r in g.itertuples() if r.VMDa_Total}
    return _CACHE["pnct"]


def portas(municipio: str) -> list[dict]:
    """Os trechos de acesso que a base do DNIT associa a este município."""
    if "vdm" not in _CACHE:
        _CACHE["vdm"] = gpd.read_file(VDM) if VDM.exists() else None
    g = _CACHE["vdm"]
    if g is None:
        return []
    alvo = _ch(municipio)
    saida = []
    for r in g.itertuples():
        if alvo and alvo in _ch(r.municipio):
            saida.append({
                "rodovia": str(r.rodovia), "porta": str(r.tipo_porta),
                "veiculos_dia": int(r.vdm_veic_dia or 0),
                "classe": str(r.classe_volume),
                "perfil": str(r.perfil_trafego),
                "pista": str(getattr(r, "tipo_pista", "") or ""),
            })
    return sorted(saida, key=lambda x: -x["veiculos_dia"])


def ferrovias(crs) -> gpd.GeoDataFrame | None:
    """Malha ferroviária, com o sentido — inclusive os trechos interrompidos.

    Na faixa não há ferrovia de passageiros: o que existe é carga, e boa
    parte está interrompida. A camada distingue as duas situações porque a
    diferença entre elas é o que interessa ao turismo.
    """
    if "fer" not in _CACHE:
        if not FERROVIAS.exists():
            _CACHE["fer"] = None
        else:
            g = gpd.read_file(f"zip://{FERROVIAS}").to_crs(crs)
            g["interrompida"] = (g.Sentido.astype(str).str.strip().str.lower()
                                 == "interrompido")
            _CACHE["fer"] = g
    return _CACHE["fer"]
