# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
NOMES OFICIAIS DOS PONTOS DE AFERICAO
================================================================================
A lista valida dos pontos e a da aba "sintese pontos de coleta" de
`Dados Pesquisa de campo 4.2 Unesco.csv.xlsx` — a analise final de campo. Este
script traz dela, para a camada consolidada:

    nome_ponto              o nome do local, como na sintese
    area_analise            o que o ponto e (rotatoria, terminal, aduana...)
    classificacao_turistica a classificacao declarada

A AREA DE ANALISE E O CAMPO QUE FALTAVA
    Dois pontos de Foz se chamam "Avenida das Cataratas" na sintese, a 9 km um
    do outro. Pelo nome sao indistinguiveis; pela area de analise, nao: um e
    "rotatoria, via de acesso interna ao sul do municipio" e o outro e "via
    interna de acesso aos atrativos turisticos principais". Foi esse campo que
    desfez a confusao, e e ele que evita que ela se repita — Bonito tem tres
    acessos estaduais, Ponta Pora tem dois.

PAREAMENTO
    Por ORDEM dentro do municipio, depois de retirar da sintese os pontos que
    a coordenacao excluiu da analise (EXCLUIDOS, abaixo). A ordem da sintese e
    a ordem de visitacao, e e a mesma da camada. O script mostra o cotejo e
    lista os pares de baixa semelhanca entre os nomes (abaixo de 0,55). Sem
    --aplicar, nada e gravado; com --aplicar, todos os pares sao gravados,
    inclusive os de baixa semelhanca. Por isso a conferencia vem antes.

USO
    python 31_nomes_oficiais_pontos.py            # so confere e mostra
    python 31_nomes_oficiais_pontos.py --aplicar  # grava na camada
================================================================================
"""
from __future__ import annotations

import difflib
import io
import re
import shutil
import sys
import unicodedata
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from comum import CAMPO, MUNICIPIOS                              # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PLANILHA = (CAMPO / "03_Pontos_Afericao" /
            "Dados Pesquisa de campo 4.2 Unesco.csv.xlsx")
ABA = "síntese pontos de coleta"
CONSOLIDADO = (CAMPO / "03_Pontos_Afericao" / "vetores_gis" /
               "pontos_afericao_consolidados.geojson")
BACKUP = CONSOLIDADO.with_name("pontos_afericao_consolidados_ORIGINAL.geojson")
APLICAR = "--aplicar" in sys.argv

# Pontos da sintese que a coordenacao deixou fora da analise: nao estao na
# camada e nao entram. Chave: (municipio, trecho do nome na sintese).
EXCLUIDOS = {
    ("Medianeira", "centro urbano rotas para atrativos"),
    ("Campo Grande", "br 262"),        # o segundo BR-262 (acesso oeste)
}


def ch(s: str) -> str:
    t = unicodedata.normalize("NFKD", str(s or ""))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def sintese() -> dict[str, list[dict]]:
    d = pd.read_excel(PLANILHA, sheet_name=ABA, header=None)
    d[1] = d[1].ffill()
    d = d[d[2].notna() & (d[2].astype(str).str.strip() != "")
          & (d[2].astype(str) != "nome do local")]
    nomes = {ch(m.nome): m.nome for m in MUNICIPIOS}
    saida: dict[str, list[dict]] = {}
    for r in d.itertuples():
        mun = re.sub(r"\s*\(.*?\)\s*$", "", str(r._2)).strip()
        alvo = nomes.get(ch(mun))
        if not alvo:
            continue
        nome = re.sub(r"\s+", " ", str(r._3)).strip()
        saida.setdefault(alvo, []).append({
            "nome": nome,
            "area": re.sub(r"\s+", " ", str(r._4)).strip(),
            "classe": re.sub(r"\s+", " ", str(r._5)).strip(),
        })
    # retira os excluidos, uma vez cada
    for mun, trecho in EXCLUIDOS:
        lista = saida.get(mun, [])
        for i, it in enumerate(lista):
            if trecho in ch(it["nome"]):
                if mun == "Campo Grande" and i == 0:
                    continue            # o primeiro BR-262 é o que fica
                del lista[i]
                break
    return saida


S = sintese()
g = gpd.read_file(CONSOLIDADO)
for col in ("area_analise", "classificacao_turistica"):
    if col not in g.columns:
        g[col] = None

mudancas, alerta = [], []
for m in MUNICIPIOS:
    itens = S.get(m.nome, [])
    sub = g[g.cidade == m.nome].copy()
    sub["n"] = sub.ordem.astype(str).str.extract(r"(\d+)").astype(float)
    sub = sub.sort_values("n")
    if len(itens) != len(sub):
        alerta.append(f"{m.nome}: síntese {len(itens)} × camada {len(sub)}")
        continue
    print(f"\n── {m.nome}")
    for (idx, atual), novo in zip(sub.iterrows(), itens):
        sim = difflib.SequenceMatcher(
            None, ch(atual.nome_ponto), ch(novo["nome"])).ratio()
        sinal = " " if sim >= 0.55 else "≠"
        print(f"  {sinal} {str(atual.ordem):<10} {str(atual.nome_ponto)[:44]:<44}"
              f" → {novo['nome'][:46]}")
        if sim < 0.55:
            alerta.append(f"{m.nome} {atual.ordem}: "
                          f"'{atual.nome_ponto}' → '{novo['nome']}' "
                          f"(semelhança {sim:.2f})")
        mudancas.append((idx, novo, str(atual.nome_ponto)))

print("\n" + "=" * 78)
if alerta:
    print("PARES DE BAIXA SEMELHANÇA — conferir antes de gravar:")
    for a in alerta:
        print("   " + a)
print(f"{len(mudancas)} pontos pareados de {len(g[g.cidade.isin([m.nome for m in MUNICIPIOS])])} na camada")

if not APLICAR:
    print("\nNada gravado. Use --aplicar depois de conferir o cotejo acima.")
    raise SystemExit

if not BACKUP.exists():
    shutil.copy2(CONSOLIDADO, BACKUP)
n = 0
for idx, novo, antes in mudancas:
    g.at[idx, "area_analise"] = novo["area"]
    g.at[idx, "classificacao_turistica"] = novo["classe"]
    if str(g.at[idx, "nome_ponto"]) != novo["nome"]:
        g.at[idx, "nome_ponto"] = novo["nome"]
        marca = (f"{date.today():%Y-%m-%d}: nome da síntese de campo "
                 f"(era '{antes}').")
        atual = g.at[idx, "correcao"] if "correcao" in g.columns else None
        g.at[idx, "correcao"] = (f"{atual} {marca}".strip()
                                 if atual and str(atual) != "None" else marca)
        n += 1
# ── ROTULO: o nome oficial, desambiguado quando se repete ──────────────────
# A sintese chama de "BR-163 (rodovia federal)" dois pontos de Capanema, e de
# "Avenida das Cataratas" dois de Foz. Em qualquer listagem, dois itens com o
# mesmo nome sao indistinguiveis. O rotulo e entao o nome oficial
# mais um qualificador tirado da area de analise — que e justamente o campo
# que os distingue. O nome_ponto continua sendo o da sintese, intocado.
# Do mais específico para o mais genérico: a primeira regra que casar vence,
# e "acesso externo e a atrativos" tem de ganhar de "acesso externo".
QUALIF = [
    (r"aduana", "aduana"),
    (r"aeroporto", "aeroporto"),
    (r"terminal de passageiros", "terminal"),
    (r"e a atrativos|a atrativos tur[íi]sticos", "acesso externo e a atrativos"),
    (r"atrativos tur[íi]sticos principais", "acesso aos atrativos"),
    (r"acesso .*atrativo|rota para atrativo", "acesso a atrativos"),
    (r"interna ao sul", "acesso interno ao sul"),
    (r"acesso externa a?s? acts|acesso .*acts", "acesso às ACTs"),
    (r"externa ao munic|de acesso ao munic", "acesso externo"),
    (r"interna ao munic|acesso interno|vias internas", "acesso interno"),
    (r"lazer", "área de lazer"),
    (r"rotat[óo]ria", "rotatória"),
]


def qualificador(area: str) -> str:
    a = ch(area)
    for padrao, rot in QUALIF:
        if re.search(padrao, a):
            return rot
    return re.sub(r"\s+", " ", str(area)).strip()[:26]


# ── a aduana nao e a ponte ─────────────────────────────────────────────────
# Em tres pontos a sintese nomeia a travessia e a area de analise diz que o
# objeto aferido e a aduana: Foz (Amizade e Tancredo Neves) e Capanema (Rio
# Santo Antonio). A ficha preenchida e a de Aduanas — guiches, setores,
# fluxos de entrada e saida —, nao a da ponte como ligacao rodoviaria, que
# consta da malha de rodovias. Sem a distincao, a mesma ponte apareceria duas
# vezes e com avaliacoes diferentes.
#
# O nome_ponto continua o da sintese. Quem muda e o rotulo, que e nosso.
def nomear_aduana(nome: str, area: str) -> str:
    if not ch(area).startswith("aduana"):
        return nome
    if re.search(r"aduan|alf[âa]ndeg|receita|inspetoria", nome, re.I):
        return nome
    corpo = re.split(r"\s+[-–]\s+", nome, maxsplit=1)[0].strip()
    artigo = "da " if re.match(r"(?i)ponte\b", corpo) else ""
    return f"Aduana {artigo}{corpo}"


if "rotulo" not in g.columns:
    g["rotulo"] = None
duplicados, aduanas = [], []
for m in MUNICIPIOS:
    sub = g[g.cidade == m.nome]
    contagem = sub.nome_ponto.astype(str).value_counts()
    for idx, r in sub.iterrows():
        nome = str(r.nome_ponto)
        base = nomear_aduana(nome, r.area_analise)
        if contagem.get(nome, 0) > 1:
            q = qualificador(r.area_analise)
            g.at[idx, "rotulo"] = f"{base} — {q}"
            duplicados.append(f"{m.nome} {r.ordem}: {base} — {q}")
        else:
            g.at[idx, "rotulo"] = base
        if base != nome:
            aduanas.append(f"{m.nome} {r.ordem}: {nome}  ->  {base}")

g.to_file(CONSOLIDADO, driver="GeoJSON")
gpkg = CONSOLIDADO.with_suffix(".gpkg")
if gpkg.exists():
    g.to_file(gpkg, driver="GPKG")
print(f"\n{n} nomes alinhados à síntese · área de análise e classificação "
      f"gravadas em {len(mudancas)} pontos")
if aduanas:
    print(f"\n{len(aduanas)} pontos rotulados como aduana (o nome da "
          "síntese é o da travessia):")
    for a in aduanas:
        print("   " + a)
if duplicados:
    print(f"\n{len(duplicados)} nomes repetidos dentro do município — "
          "rótulo desambiguado pela área de análise:")
    for d in duplicados:
        print("   " + d)
