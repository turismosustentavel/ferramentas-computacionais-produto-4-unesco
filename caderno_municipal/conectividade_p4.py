# -*- coding: utf-8 -*-
"""
Conectividade digital dos doze municipios.

Terceira dimensao da analise, ao lado de infraestrutura e mobilidade. A
planilha `Dados conectividade - Fronteira.xlsx` cobre os doze municipios com
os indicadores da ANATEL e a presenca das plataformas de aplicativo.

Tres cuidados que a leitura crua nao tem:

- os numeros vem como texto com virgula decimal;
- na planilha, a coluna "HHI" ja e o componente de COMPETITIVIDADE do IBC,
  medido pelo inverso do indice de Herfindahl-Hirschman: quanto maior, mais
  competitivo o mercado (pagina do IBC na ANATEL, conferida em 02/10/2026);
- "Fibra" e a existencia de backhaul de fibra optica no municipio, e nao a
  proporcao de domicilios: onze municipios tem 100 e empatam.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import json

import pandas as pd

from comum import ACERVO, DIR_DADOS, MUNICIPIOS

ARQUIVO = (ACERVO / "06_Dados_Processados_Pipeline" /
           "Planilhas_Consolidadas" / "Dados conectividade - Fronteira.xlsx")
# Conferência nas listas oficiais de cidades atendidas (29/09/2026):
# prevalece sobre a planilha para as plataformas
# nacionais. Medianeira tinha Uber marcado como "Não tem" e está na lista da
# Uber; o aiqfome, que a planilha trazia como aplicativo local em dois
# municípios, é plataforma nacional e está na lista de sete.
VERIFICADAS = DIR_DADOS / "plataformas" / "plataformas_listas_oficiais.json"

# (coluna na planilha, rótulo, maior é melhor?, unidade)
INDICADORES = [
    ("IBC", "Índice Brasileiro de Conectividade", True, ""),
    ("Cobertura Pop. 4G5G", "Cobertura da população por 4G/5G", True, "%"),
    ("Densidade SMP", "Densidade do serviço móvel", True, ""),
    ("Densidade SCM", "Densidade da banda larga fixa", True, ""),
    ("Adensamento Estações", "Adensamento de estações", True, ""),
    ("Fibra", "Rede de transporte em fibra óptica", True, ""),
    ("Cobertura área agricultável", "Cobertura da área agricultável",
     True, "%"),
    ("HHI SMP", "Competitividade do mercado móvel (HHI)", True, ""),
    ("HHI SCM", "Competitividade da banda larga fixa (HHI)", True, ""),
]

PLATAFORMAS = [("99", "99"), ("Uber", "Uber"), ("Ifood", "iFood")]
LOCAIS = [("App de mobilidade local", "mobilidade local"),
          ("App de delivery local", "delivery local")]
# As plataformas de entrega (iFood, aiqfome) saíram em 29/09: não tratam de
# mobilidade nem de conectividade (decisão do usuário). Ficam as nacionais
# de transporte por aplicativo e os aplicativos locais de mobilidade.
NACIONAIS = [("99", "transporte"), ("Uber", "transporte")]


def verificadas() -> dict:
    try:
        return json.loads(VERIFICADAS.read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def presenca(slug: str, linha) -> tuple[dict, dict]:
    """({plataforma: está?}, {plataforma: 'lista oficial' | 'planilha'})."""
    v = (verificadas().get("municipios") or {}).get(slug) or {}
    col = {rot: c for c, rot in PLATAFORMAS}
    tem, fonte = {}, {}
    for rot, _ in NACIONAIS:
        if v.get(rot) is not None:
            tem[rot], fonte[rot] = bool(v[rot]), "lista oficial"
        elif rot in col:
            tem[rot] = str(linha[col[rot]]).strip().lower().startswith("tem")
            fonte[rot] = "planilha"
        else:   # aiqfome sem conferência: o que a planilha trouxer
            tem[rot] = "aiqfome" in str(linha["App de delivery local"]).lower()
            fonte[rot] = "planilha"
    return tem, fonte


def _sem_nacionais(txt: str) -> str:
    """Os aplicativos locais, sem as plataformas nacionais."""
    nomes = [x.strip() for x in re.split(r",|/", txt) if x.strip()]
    nomes = [x for x in nomes if x.lower() not in ("aiqfome", "-", "nan")]
    return ", ".join(nomes)


def _ch(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore")
    return re.sub(r"[^a-z]", "", s.decode().lower())


def _num(v) -> float | None:
    s = str(v).strip()
    if not s or s in ("-", "nan", "None"):
        return None
    s = s.replace(".", "").replace(",", ".") if "," in s else s
    try:
        return float(s)
    except ValueError:
        return None


_CACHE: dict | None = None


def tabela() -> pd.DataFrame | None:
    """Uma linha por município do estudo, com o slug do caderno."""
    global _CACHE
    if _CACHE is None:
        if not ARQUIVO.exists():
            _CACHE = {"df": None}
        else:
            d = pd.read_excel(ARQUIVO)
            # a coluna da "99" chega como inteiro, e não como texto
            d.columns = [str(c).strip() for c in d.columns]
            por_chave = {_ch(m.nome): m for m in MUNICIPIOS}
            d["slug"] = [
                (por_chave[_ch(n)].slug if _ch(n) in por_chave else None)
                for n in d.Municipio]
            d = d[d.slug.notna()].copy()
            for col, _, _, _ in INDICADORES:
                d[col] = d[col].map(_num)
            _CACHE = {"df": d.reset_index(drop=True)}
    return _CACHE["df"]


def do_municipio(slug: str) -> dict | None:
    """Os indicadores do município, já com a posição entre os doze."""
    d = tabela()
    if d is None or slug not in set(d.slug):
        return None
    linha = d[d.slug == slug].iloc[0]
    n = len(d)
    saida = {"n_municipios": int(n), "indicadores": []}
    for col, rot, maior_melhor, uni in INDICADORES:
        v = linha[col]
        if pd.isna(v):
            continue
        # a posição respeita o sentido de cada indicador (todos: maior é melhor)
        pos = int(d[col].rank(ascending=not maior_melhor,
                              method="min")[linha.name])
        saida["indicadores"].append({
            "coluna": col, "rotulo": rot, "valor": float(v), "unidade": uni,
            "maior_e_melhor": bool(maior_melhor), "posicao": pos,
            "minimo": float(d[col].min()), "maximo": float(d[col].max()),
            "media": round(float(d[col].mean()), 2),
        })
    saida["plataformas"], saida["fonte_plataformas"] = presenca(slug, linha)
    saida["locais"] = {rot: _sem_nacionais(str(linha[col]))
                       for col, rot in LOCAIS}
    return saida


def grade_plataformas() -> list[dict]:
    """Os doze municípios e as plataformas presentes em cada um."""
    d = tabela()
    if d is None:
        return []
    ordem = {m.slug: m.ordem for m in MUNICIPIOS}
    nomes = {m.slug: m.nome for m in MUNICIPIOS}
    linhas = []
    for _, r in d.iterrows():
        locais = [x for x in (_sem_nacionais(str(r["App de mobilidade local"])),)
                  if x]
        tem, fonte = presenca(r.slug, r)
        linhas.append({
            "slug": r.slug, "nome": nomes.get(r.slug, r.Municipio),
            "ordem": ordem.get(r.slug, 99), **tem, "fonte": fonte,
            "locais": ", ".join(locais),
        })
    return sorted(linhas, key=lambda x: x["ordem"])
