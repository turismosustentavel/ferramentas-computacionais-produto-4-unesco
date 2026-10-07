# -*- coding: utf-8 -*-
"""
A rede intermunicipal de onibus: DER-PR e AGEMS.

A ANTT regula o transporte INTERESTADUAL e internacional. A ligacao dentro
do estado nao e competencia dela: quem regula a linha Foz do Iguacu-Cascavel
e o DER-PR, e a Campo Grande-Corumba, a AGEMS. Na base da ANTT, as ligacoes
dentro do estado aparecem apenas como secoes de linha interestadual vendidas
em trecho, nao como linha estadual.

A camada usada aqui traz as linhas estaduais com geometria sobre a rodovia,
frequencia, extensao, tempo medio e tarifa media.

Ao contrario das ligacoes da ANTT, que sao linhas de desejo retas entre
origem e destino, estas seguem a estrada: e o traçado real do corredor.
"""
from __future__ import annotations

import geopandas as gpd

from comum import PRODUCAO

ARQ = (PRODUCAO / "11_transporte_regional_intra_faixa"
       / "linhas_onibus_intra_faixa_fronteira.geojson")
COR = "#eb6834"                  # laranja categórico; o azul é da ANTT
_CACHE: dict = {}


def _num(v, padrao=0):
    try:
        return int(float(str(v).replace(",", ".")))
    except (TypeError, ValueError):
        return padrao


def linhas(crs):
    """As linhas estaduais, reprojetadas para `crs`."""
    chave = str(crs)
    if chave not in _CACHE:
        if not ARQ.exists():
            return None
        g = gpd.read_file(ARQ).to_crs(crs)
        g["partidas"] = g["partidas"].map(_num)
        _CACHE[chave] = g
    return _CACHE[chave]


def do_municipio(geom_municipio, crs, folga_m: float = 3000.0):
    """As linhas que passam pelo município, com a folga do traçado.

    A folga existe porque a geometria da linha é generalizada: um corredor
    que tangencia o limite pode passar algumas centenas de metros fora dele
    sem deixar de servir o município.
    """
    g = linhas(crs)
    if g is None or g.empty or geom_municipio is None:
        return None
    sub = g[g.intersects(geom_municipio.buffer(folga_m))]
    return sub if len(sub) else None


def descrever(linha) -> dict:
    """Os atributos da linha: rodovias, viações, frequência, extensão, tempo e tarifa."""
    return {
        "nome": str(linha.nome_linha),
        "rodovias": str(linha.rodovias),
        "viacoes": str(linha.viacoes),
        "tipo": str(linha.tipo_linha),
        "partidas_dia": _num(linha.partidas),
        "frequencia": str(linha.frequencia),
        "extensao_km": float(linha.ext_km),
        "tempo": str(linha.tempo_med),
        "tarifa": str(linha.tarifa_med),
    }
