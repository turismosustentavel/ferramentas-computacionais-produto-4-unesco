# -*- coding: utf-8 -*-
"""
A rodoviaria e o aeroporto, comparados entre os doze municipios.

Cada municipio tem exatamente uma rodoviaria, e seis tem aeroporto. Uma grade
de um so ponto seria um checklist: diria que a rodoviaria daqui tem
guarda-volumes, e nada mais. Comparada com as outras onze, a mesma linha
passa a dizer se isso e comum ou raro na faixa — que e o que interessa ao
caderno.

Le direto dos formularios, sem depender de a ficha individual ter sido
gerada, porque a comparacao precisa dos doze de uma vez.
"""
from __future__ import annotations

import pandas as pd

import fichas_p4 as fp
from comum import DIR_DADOS, MUNICIPIOS
from presencas_p4 import _chave

_CACHE: dict = {}


def _vinculo() -> pd.DataFrame:
    if "v" not in _CACHE:
        d = pd.read_excel(DIR_DADOS / "vinculo_fichas_pontos.xlsx",
                          sheet_name="Vínculo")
        _CACHE["v"] = d[d.vinculado].copy()
    return _CACHE["v"]


def municipios_com(formulario: str) -> list:
    """Os municípios do caderno que têm ficha desse formulário, em ordem."""
    v = _vinculo()
    v = v[v["formulário"] == formulario]
    tem = set()
    for r in v.itertuples():
        for m in MUNICIPIOS:
            if str(r.municipio_do_ponto).startswith(m.nome):
                tem.add(m.slug)
    return [m for m in MUNICIPIOS if m.slug in tem]


def presencas_por_municipio(formulario: str) -> dict[str, dict[str, bool]]:
    """{slug: {item normalizado: existe}} para um formulário."""
    chave = f"p_{formulario}"
    if chave not in _CACHE:
        v = _vinculo()
        v = v[v["formulário"] == formulario]
        saida: dict[str, dict[str, bool]] = {}
        for r in v.itertuples():
            alvo = next((m.slug for m in MUNICIPIOS
                         if str(r.municipio_do_ponto).startswith(m.nome)),
                        None)
            if not alvo:
                continue
            reg = fp.registro(formulario, r.linha_csv)
            # dois pontos do mesmo formulário no município (Foz tem duas
            # aduanas): o item existe se existir em algum deles
            d = saida.setdefault(alvo, {})
            for nome, tem in fp.presencas(formulario, reg):
                c = _chave(nome)
                d[c] = bool(d.get(c)) or bool(tem)
        _CACHE[chave] = saida
    return _CACHE[chave]


def grade(formulario: str, temas) -> dict:
    """Grade item × município, no mesmo formato de `presencas_p4.grade`."""
    por_mun = presencas_por_municipio(formulario)
    muns = [m for m in municipios_com(formulario) if m.slug in por_mun]
    linhas = []
    for tema, itens in temas:
        for rotulo, nomes in itens:
            chaves = [_chave(x) for x in nomes]
            estados = []
            for m in muns:
                achados = [por_mun[m.slug][c] for c in chaves
                           if c in por_mun[m.slug]]
                estados.append(any(achados) if achados else None)
            if any(e is not None for e in estados):
                linhas.append((tema, rotulo, estados))
    return {"linhas": linhas,
            "municipios": [{"slug": m.slug, "nome": m.nome} for m in muns]}
