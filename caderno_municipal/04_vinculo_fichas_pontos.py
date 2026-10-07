# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
FASE 1c - VINCULO ENTRE FICHAS DE CAMPO E PONTOS DE AFERICAO
================================================================================
OBJETIVO
    Ligar cada ficha de campo ao ponto de afericao mapeado, para que toda
    informacao levantada seja georreferenciada e atribuida ao municipio certo.

FONTE DE VERDADE DOS PONTOS
    pontos_afericao_consolidados.geojson (89 pontos), que traz 'ordem',
    'categoria' e - decisivo - 'formulario': qual formulario foi aplicado em
    cada ponto.

    Por que esta camada e nao os pinos das listas do Google: em Corumba, os
    pontos de rodovia desta camada caem sobre o eixo da BR-262 do SNV/DNIT
    (2 a 15 m de distancia), enquanto os pinos do Google ficam de 1,2 a 3,1 km
    fora dele. Os pinos foram largados por aproximacao; servem para identificar
    qual ponto e qual, nao para posiciona-lo.

METODO
    1. O campo 'formulario' restringe os candidatos: uma ficha de rodoviaria so
       pode casar com um ponto marcado como Formulario Rodoviarias. Isso reduz
       o espaco de busca de dezenas para poucas unidades.
    2. Dentro de cada par (municipio x formulario) faz-se atribuicao OTIMA
       um-para-um por similaridade de nome, e nao escolha gulosa independente.
       Sem isso, duas fichas disputam o mesmo ponto e ambas erram.
    3. Rotulos genericos ("P3", "Rotatoria") nao casam por nome - sao resolvidos
       pelo rotulo dos pinos de campo (script 05) ou por eliminacao, quando a
       atribuicao um-para-um deixa um unico par possivel.

SAIDA
    02_Dados_Municipais/vinculo_fichas_pontos.xlsx
================================================================================
"""
from __future__ import annotations

import difflib
import io
import re
import sys
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).parent))
from comum import (  # noqa: E402
    CAMPO, JOTFORM, DIR_DADOS, MUNICIPIOS, normalizar_municipio,
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

VAZIAS = {"de", "da", "do", "das", "dos", "com", "e", "a", "o", "em", "no",
          "na", "para", "ao", "as", "os", "entre"}


def chave(s) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    t = unicodedata.normalize("NFKD", str(s))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-zA-Z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def tokens(s: str) -> set[str]:
    return {t for t in chave(s).split() if t and t not in VAZIAS}


def similar(a: str, b: str) -> float:
    """Sequencia + contencao de tokens.

    As fontes usam vocabularios diferentes para o mesmo lugar ("Br272 com 163"
    x "BR-163 (rodovia federal)"). A razao de sequencia pura penaliza a
    diferenca de comprimento; a contencao corrige isso. Exige dois tokens uteis
    para nao casar rotulo generico de uma palavra.
    """
    ka, kb = chave(a), chave(b)
    if not ka or not kb:
        return 0.0
    seq = difflib.SequenceMatcher(None, ka, kb).ratio()
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return seq
    menor = min(len(ta), len(tb))
    cont = len(ta & tb) / menor if menor >= 2 else 0.0
    return max(seq, cont)


# ==============================================================================
# 1. PONTOS - CAMADA CONSOLIDADA
# ==============================================================================
CONSOLIDADO = (CAMPO / "03_Pontos_Afericao" / "vetores_gis" /
               "pontos_afericao_consolidados.geojson")
cons = gpd.read_file(CONSOLIDADO)
cons["cod_municipio"] = cons["cidade"].map(
    lambda v: (normalizar_municipio(v).codigo_ibge
               if normalizar_municipio(v) else pd.NA))
cons = cons[cons.cod_municipio.notna()].copy()
cons["cod_municipio"] = cons["cod_municipio"].astype(int)
print(f"Camada consolidada: {len(cons)} pontos em "
      f"{cons.cod_municipio.nunique()} municípios")
for k, n in cons.formulario.value_counts().items():
    print(f"    {k:<26} {n:>3}")

FORM_CONSOLIDADO = {
    "Geral": "Formulário Geral",
    "Rodoviária": "Formulário Rodoviárias",
    "Aeroporto": "Formulário Aeroportos",
    "Aduana": "Formulário Aduanas",
}

# ------------------------------------------------------------------------------
# CONFIRMACOES DA COORDENACAO DO ESTUDO (22/09/2026)
# ------------------------------------------------------------------------------
# Vinculos informados diretamente por quem esteve em campo. Prevalecem sobre
# qualquer casamento automatico.
# (codigo IBGE da ficha, formulario, texto na ficha) -> (codigo do ponto, ordem)
# O codigo do ponto pode diferir do da ficha: na conurbacao Barracao x Dionisio
# Cerqueira houve fichas preenchidas sob um municipio para pontos do outro.
OVERRIDES: dict[tuple[int, str, str], tuple[int, str]] = {
    (4115804, "Geral", "rotatoria"): (4115804, "Ponto #1"),   # Medianeira

    # --- Conurbação Barracão (PR) x Dionísio Cerqueira (SC) ------------------
    # O proprio catalogo de campo registra a troca, na coluna de referencia:
    #   DC "P1: Rotatoria ligacao BR-280 com BR-163" <- ref "Acesso Viario (Barracão)"
    #   DC "P2: centro urbano conurbado"             <- ref "P3 (Barracão)"
    # Sao fichas preenchidas como Barracao para pontos de Dionisio Cerqueira.
    # A cronologia do carimbo de envio (04/08: 10:11, 10:26, 10:51) confirma a
    # sequencia relatada - 1o Rua Minas Gerais, 2o o ponto da Triplice
    # Fronteira, 3o o centro urbano conurbado:
    (4102604, "Geral", "p1"): (4102604, "Ponto #5"),   # Praça de Lazer / R. Minas Gerais
    (4102604, "Geral", "p2"): (4102604, "Ponto #4"),   # Tríplice Fronteira
    (4102604, "Geral", "p3"): (4205001, "Ponto #4"),   # centro urbano conurbado, em DC
    (4102604, "Geral", "acesso viario"): (4205001, "Ponto #1"),
    (4205001, "Geral", "ponto rural sul"): (4205001, "Ponto #2"),
    (4102604, "Geral", "ponto estrada rural norte"): (4102604, "Ponto #2"),
    (4102604, "Geral", "ponto rural norte 2"): (4102604, "Ponto #1"),
    # Foz do Iguacu: o casamento por nome nao enxerga a correspondencia entre a
    # aduana e a ponte. A Ponte Internacional da Amizade liga a Ciudad del Este
    # (Paraguai); a Ponte Tancredo Neves liga a Puerto Iguazu (Argentina).
    (4108304, "Aduana", "aduana do paraguai"): (4108304, "Ponto #9"),
    (4108304, "Aduana", "aduana da argentina"): (4108304, "Ponto #10"),
    # Foz do Iguacu - lista compartilhada do Google. Os tres primeiros vieram do
    # cruzamento do pino com o ponto consolidado (8 m, 56 m e 303 m).
    (4108304, "Geral", "br 277 com perimetral"): (4108304, "Ponto #1"),
    (4108304, "Geral", "br277 com costa e silva"): (4108304, "Ponto #2"),
    (4108304, "Geral", "rota de acesso sul proximo catuai"): (4108304, "Ponto #3"),
    # "P1: acesso atrativos" = pino "P1: ponto de interesse turistico".
    (4108304, "Geral", "p1 acesso atrativos"): (4108304, "Ponto #4"),
    # "Praca proximo ao shopping" = catalogo "P2: Parque em frente ao Shopping
    # JL" = pino "P2", que esta sobre a Praca Naipi e Tarobo.
    (4108304, "Geral", "praca proximo ao shopping"): (4108304, "Ponto #5"),
    # Mercado Publico Barrageiro (Vila A): a camada consolidada foi corrigida
    # pelo 18_corrigir_camada_pontos.py - o antigo "#6 aduana" era duplicata
    # do #2 e passou a ser este ponto, levantado em campo como "P3".
    (4108304, "Geral", "p3"): (4108304, "Ponto #6"),

    # Medianeira: das rotas de acesso na PR-495, so a "rota de acesso ao
    # interior" foi levantada - e e essa que a ficha "Acesso PR serranopolis"
    # registra. Nao ha contradicao com o trecho nao levantado.
    (4115804, "Geral", "acesso pr serranopolis"): (4115804, "Ponto #2"),

    # Guaira: a equipe nao esteve em nenhuma instalacao da Receita Federal. O
    # que foi levantado foi a balsa. O Ponto #8 esta nomeado como "Inspetoria
    # da Receita Federal" na camada, mas corresponde a travessia por balsa.
    (4108809, "Aduana", "balsa guaira"): (4108809, "Ponto #8"),
}

# Pontos levantados em campo que NAO existem na camada consolidada e precisam
# ser acrescentados. Cada um tem ficha preenchida e pino, mas nenhum registro
# na camada de 89 pontos.
A_ACRESCENTAR = [
    (4115804, "Medianeira (PR)", "BR de acesso a Medianeira",
     "(a georreferenciar)",
     "Consta da sequência de campo como etapa distinta da rotatória (Ponto #1) "
     "e da rota de acesso ao interior na PR-495 (Ponto #2)."),
]

# Pontos que constam do planejamento mas NAO foram levantados. Registrados para
# que a ausencia de ficha seja lida como decisao de campo, e nao como falha.
NAO_LEVANTADOS = [
    (5003207, "Porto Seco da Agesa",
     "Pinado no planejamento, não levantado."),
    (5003207, "Estação Ferroviária de Albuquerque",
     "Pinado no planejamento, não levantado."),
    (5006903, "Aeroporto Municipal de Porto Murtinho",
     "Não levantado: é apenas aeródromo, sem operação de passageiros que "
     "justifique a ficha de aeroporto. Decisão técnica de campo, não lacuna."),
    (4102604, "Barracão ponto 2",
     "Ausente da sequência de campo relatada; pino existe na lista do Google "
     "mas o ponto não foi visitado."),
    (4115804, "Rota de acesso fora do perímetro urbano",
     "Pulada em campo por estar muito próxima da rota de acesso ao interior."),
    (4115804, "PR-495 km 3582–3822",
     "Trecho não levantado."),
]

# ==============================================================================
# 2. CATALOGO DESCRITIVO - traduz o texto da ficha para o rotulo do ponto
# ==============================================================================
xls = pd.ExcelFile(JOTFORM / "georreferenciamento.xlsx")
cat = pd.concat([
    xls.parse("Pontos de coleta PR + Mundo Nov"),
    xls.parse("Pontos de coleta MS").rename(columns={
        "municipio": "Município", "nome_ponto_afericao": "Ponto de Coleta"}),
], ignore_index=True)
cat = cat[cat["Ponto de Coleta"].notna() & cat["referencia jetform"].notna()].copy()
cat["cod_mun"] = cat["Município"].map(
    lambda v: (normalizar_municipio(v).codigo_ibge
               if normalizar_municipio(v) else pd.NA))


def via_catalogo(cod_mun: int, texto_ficha: str) -> str:
    """Traduz o texto livre da ficha para o nome do ponto no catálogo."""
    m = cat[cat.cod_mun == cod_mun]
    if m.empty:
        return ""
    exato = m[m["referencia jetform"].map(chave) == chave(texto_ficha)]
    if len(exato):
        return str(exato.iloc[0]["Ponto de Coleta"])
    melhor, sc = "", 0.0
    for _, c in m.iterrows():
        s = similar(texto_ficha, c["referencia jetform"])
        if s > sc:
            melhor, sc = str(c["Ponto de Coleta"]), s
    return melhor if sc >= 0.72 else ""


# ==============================================================================
# 3. LEITURA DAS FICHAS
# ==============================================================================
FORMULARIOS = [
    ("Geral",      "Formulário_Geral_-_Produto_04*.csv",
     "Município de coleta", "Ponto de análise"),
    ("Rodoviária", "Formulário_Rodoviárias_-_Produt*.csv", "Município", "Nome"),
    ("Aeroporto",  "Formulário_Aeroportos_-_Produto*.csv",
     "Município", "Nome do aeroporto"),
    ("Aduana",     "Formulário_Aduanas_-_Produto_04*.csv",
     "Município", "Nome da aduana"),
]

fichas: list[dict] = []
for rotulo, padrao, col_mun, col_nome in FORMULARIOS:
    arq = sorted(JOTFORM.glob(padrao))[0]
    for enc in ("utf-8", "latin-1"):
        try:
            df = pd.read_csv(arq, encoding=enc, low_memory=False)
            break
        except UnicodeDecodeError:
            continue
    for i, r in df.iterrows():
        mun = normalizar_municipio(r[col_mun])
        fichas.append({
            "formulário": rotulo,
            "linha_csv": i + 2,
            "municipio_declarado": r[col_mun],
            "municipio_ficha": mun.nome_uf if mun else "",
            "cod_municipio": mun.codigo_ibge if mun else pd.NA,
            "texto_na_ficha": r[col_nome],
            "ponto_no_catalogo": (via_catalogo(mun.codigo_ibge, r[col_nome])
                                  if mun and rotulo == "Geral" else ""),
        })
F = pd.DataFrame(fichas)

# ==============================================================================
# 4. ATRIBUICAO OTIMA POR (MUNICIPIO x FORMULARIO)
# ==============================================================================
LIMIAR = 0.45          # aceita direto pelo nome
PISO_MESMO_TIPO = 0.15 # eliminacao dentro do proprio formulario
PISO_CRUZADO = 0.30    # eliminacao que cruza formulario exige mais evidencia
F["ordem"] = ""
F["ponto_vinculado"] = ""
F["categoria"] = ""
F["lat"] = pd.NA
F["lon"] = pd.NA
F["score"] = 0.0
F["critério"] = ""
F["vinculado_tmp"] = False
F["cod_municipio_ponto"] = pd.NA
F["municipio_do_ponto"] = ""

def _fixar(fi: int, k: int, crit: str) -> None:
    F.loc[fi, ["ordem", "ponto_vinculado", "categoria", "lat", "lon", "critério"]] = [
        cons.loc[k, "ordem"], cons.loc[k, "nome_ponto"], cons.loc[k, "categoria"],
        cons.loc[k, "latitude"], cons.loc[k, "longitude"], crit]
    # O municipio do PONTO pode diferir do da ficha (conurbacao). E o do ponto
    # que vale para a analise por municipio.
    F.loc[fi, "cod_municipio_ponto"] = cons.loc[k, "cod_municipio"]
    F.loc[fi, "municipio_do_ponto"] = f"{cons.loc[k, 'cidade']} ({cons.loc[k, 'uf']})"
    F.loc[fi, "vinculado_tmp"] = True


# --- confirmacoes da coordenacao, aplicadas antes de qualquer heuristica -----
for (cod_o, form_o, txt_o), (cod_pt, ordem_o) in OVERRIDES.items():
    alvo = cons[(cons.cod_municipio == cod_pt) & (cons.ordem == ordem_o)]
    if alvo.empty:
        print(f"  [aviso] override sem ponto: {cod_o}/{txt_o} -> {cod_pt}/{ordem_o}")
        continue
    sel = F[(F.cod_municipio == cod_o) & (F["formulário"] == form_o) &
            (F.texto_na_ficha.map(chave) == chave(txt_o))]
    for fi in sel.index:
        crit = "confirmado pela coordenação"
        if cod_pt != cod_o:
            crit += f" · ficha preenchida sob outro município (conurbação)"
        _fixar(fi, alvo.index[0], crit)
        F.loc[fi, "score"] = 1.0

# Duas passadas. Na primeira, cada ficha so disputa pontos do seu proprio
# formulario. So na segunda, o que sobrou de um lado encontra o que sobrou do
# outro - porque o campo 'formulario' registra o formulario PLANEJADO e houve
# caso confirmado de ponto levantado com outro (Guaicurus, em Corumba: ponto
# catalogado como Aduana, preenchido no formulario Geral).
# Sem separar as passadas, as fichas do formulario processado primeiro consomem
# os pontos dos demais e derrubam o casamento deles.
grupos = [((cod, form), g) for (cod, form), g
          in F.groupby(["cod_municipio", "formulário"], dropna=True)]

def casar(grupo: pd.DataFrame, alvos: pd.DataFrame, form: str,
          aceitar_fraco: bool) -> None:
    """Atribuição ótima um-para-um entre as fichas do grupo e os pontos alvo."""
    idx_alvo = list(alvos.index)
    custo = np.zeros((len(grupo), len(idx_alvo)))
    for a, (_, f) in enumerate(grupo.iterrows()):
        busca = [f["texto_na_ficha"]]
        if f["ponto_no_catalogo"]:
            busca.append(f["ponto_no_catalogo"])
        for b, k in enumerate(idx_alvo):
            custo[a, b] = 1.0 - max(
                similar(t, cons.loc[k, "nome_ponto"]) for t in busca)

    li, lj = linear_sum_assignment(custo)
    for a, b in zip(li, lj):
        s = 1.0 - custo[a, b]
        fi, k = grupo.index[a], idx_alvo[b]
        divergente = cons.loc[k, "formulario"] != FORM_CONSOLIDADO[form]

        # Piso de evidencia para aceitar por eliminacao. Sem ele, um rotulo
        # generico acaba amarrado a qualquer ponto que sobre - foi o que fez
        # "P3" (Foz) cair no ponto da aduana com score 0,00. Cruzar formulario
        # exige mais evidencia do que permanecer no mesmo.
        piso = PISO_CRUZADO if divergente else PISO_MESMO_TIPO
        if s >= LIMIAR:
            crit = f"nome ({s:.2f})"
        elif aceitar_fraco and s >= piso:
            crit = f"eliminação — único ponto restante ({s:.2f})"
        else:
            F.loc[fi, "critério"] = (
                f"sem evidência suficiente (melhor {s:.2f}"
                + (", e cruzaria formulário)" if divergente else ")"))
            continue
        if divergente:
            crit += (f" · formulário divergente: ponto catalogado como "
                     f"{cons.loc[k, 'formulario']}")
        F.loc[fi, "score"] = round(s, 2)
        _fixar(fi, k, crit)

    for a in set(range(len(grupo))) - set(li):
        F.loc[grupo.index[a], "critério"] = "há mais fichas do que pontos mapeados"


for passada in (1, 2):
    for (cod, form), grupo_bruto in grupos:
        grupo = grupo_bruto[~F.loc[grupo_bruto.index, "vinculado_tmp"]]
        if grupo.empty:
            continue
        usados = set(F.loc[F.cod_municipio == cod, "ordem"]) - {""}
        mesmo_tipo = cons.formulario == FORM_CONSOLIDADO[form]
        livre = (cons.cod_municipio == cod) & (~cons.ordem.isin(usados))
        alvos = cons[livre & (mesmo_tipo if passada == 1 else ~mesmo_tipo)]
        if alvos.empty:
            if passada == 2 and not F.loc[grupo.index, "critério"].any():
                F.loc[grupo.index, "critério"] = "município sem ponto disponível"
            continue
        casar(grupo, alvos, form, aceitar_fraco=(len(grupo) >= len(alvos)))

F["vinculado"] = F.ponto_vinculado.astype(str).str.len() > 0
F = F.drop(columns=["vinculado_tmp"])

# ==============================================================================
# 5. RELATORIO
# ==============================================================================
print("\n" + "=" * 80)
print("VÍNCULO FICHA -> PONTO DE AFERIÇÃO")
print("=" * 80)
res = F.groupby("formulário").agg(fichas=("vinculado", "size"),
                                  vinculadas=("vinculado", "sum")).reset_index()
res["%"] = (res.vinculadas / res.fichas * 100).round(0).astype(int)
print(res.to_string(index=False))
print(f"\nTOTAL: {int(F.vinculado.sum())} de {len(F)} fichas "
      f"({F.vinculado.mean()*100:.0f}%)")

pend = F[~F.vinculado]
if len(pend):
    print("\n" + "-" * 80)
    print(f"FICHAS SEM PONTO — {len(pend)}")
    print("-" * 80)
    for _, r in pend.iterrows():
        print(f"  [{r['formulário']:<10}] {r['municipio_ficha']:<24} "
              f"{str(r['texto_na_ficha'])[:34]:<34} {r['critério']}")

print("\n" + "-" * 80)
print("PONTOS MAPEADOS SEM FICHA CORRESPONDENTE")
print("-" * 80)
vinc = set(zip(F[F.vinculado].cod_municipio_ponto, F[F.vinculado].ordem))
sem = cons[[(c, o) not in vinc for c, o in zip(cons.cod_municipio, cons.ordem)]].copy()

# Ausencia explicada por decisao de campo nao e lacuna - e resultado.
def _justificativa(r):
    for cod, nome, motivo in NAO_LEVANTADOS:
        if cod == r["cod_municipio"] and similar(nome, r["nome_ponto"]) >= 0.60:
            return motivo
    return ""


sem["justificativa"] = sem.apply(_justificativa, axis=1)
explicados = sem[sem.justificativa != ""]
abertos = sem[sem.justificativa == ""]

if len(abertos):
    print("\n  >> SEM EXPLICAÇÃO — precisam de decisão")
    for _, r in abertos.iterrows():
        print(f"     {r['cidade']:<22} {r['ordem']:<10} "
              f"{str(r['nome_ponto'])[:44]:<44} {r['formulario']}")
if len(explicados):
    print("\n  >> NÃO LEVANTADOS POR DECISÃO DE CAMPO (registrado)")
    for _, r in explicados.iterrows():
        print(f"     {r['cidade']:<22} {r['ordem']:<10} "
              f"{str(r['nome_ponto'])[:44]}")
        print(f"        {r['justificativa'][:88]}")
print(f"\n  ({len(sem)} de {len(cons)} pontos sem ficha; "
      f"{len(abertos)} em aberto)")

print("\n" + "-" * 80)
print("PONTOS LEVANTADOS QUE FALTAM NA CAMADA CONSOLIDADA")
print("-" * 80)
for _, mun, nome, coord, obs in A_ACRESCENTAR:
    print(f"  {mun:<22} {nome}")
    print(f"      {coord}")
    print(f"      {obs[:92]}")

xlsx = DIR_DADOS / "vinculo_fichas_pontos.xlsx"
with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
    F.to_excel(w, sheet_name="Vínculo", index=False)
    if len(pend):
        pend.to_excel(w, sheet_name="Sem vínculo", index=False)
    sem.drop(columns="geometry").to_excel(w, sheet_name="Pontos sem ficha",
                                          index=False)
    pd.DataFrame(A_ACRESCENTAR,
                 columns=["cod_ibge", "município", "ponto", "coordenada",
                          "observação"]).to_excel(
        w, sheet_name="A acrescentar na camada", index=False)
print(f"\nPlanilha: {xlsx}")
