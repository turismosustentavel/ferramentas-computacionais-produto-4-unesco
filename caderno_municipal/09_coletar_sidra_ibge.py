# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
COLETA DA BASE MUNICIPAL UNIFORME - SIDRA / IBGE
================================================================================
POR QUE ESTA COLETA E NECESSARIA
    O acervo tem duas bases estaduais ricas, mas nao comparaveis entre si:
      - IPARDES (PR): series ate 2022/2026, cobre 5 dos 12 municipios;
      - SEMADESC (MS): perfis municipais publicados em 2022, mas com a maior
        parte dos indicadores ancorada no Censo 2010, cobre 6 dos 12.
    Dionisio Cerqueira (SC) nao e coberto por nenhuma das duas.

    Comparar um municipio do PR em 2022 com um do MS em 2010 produziria
    diferenca que e de fonte, nao de territorio. Por isso o caderno precisa de
    uma base unica, do mesmo ano e do mesmo metodo, para os 12 - e e o que o
    SIDRA fornece.

    As bases estaduais permanecem como enriquecimento: o IPARDES tem serie
    historica e emprego nas ACTs; a SEMADESC tem o historico de fundacao de
    cada municipio.

SAIDA
    09_Base_Socioeconomica_Municipal/03_IBGE_SIDRA/
================================================================================
"""
from __future__ import annotations

import gzip
import io
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from comum import ACERVO, MUNICIPIOS, POR_CODIGO  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DESTINO = ACERVO / "09_Base_Socioeconomica_Municipal" / "03_IBGE_SIDRA"
DESTINO.mkdir(parents=True, exist_ok=True)

COD = ",".join(str(m.codigo_ibge) for m in MUNICIPIOS)

# (rotulo, tabela, variaveis, periodo, classificacoes)
TABELAS = [
    ("populacao_area_densidade_censo2022", "4709", "allxp", "last", ""),
    # Piramide etaria: variavel 93 (populacao residente), sexo homens/mulheres
    # e os 21 grupos quinquenais da classificacao 287 - as demais das 134
    # categorias sao recortes anuais e mensais, que inflariam a consulta.
    ("populacao_sexo_idade_censo2022", "9514", "93", "last",
     "c2/4,5/c287/93070,93084,93085,93086,93087,93088,93089,93090,93091,93092,93093,93094,93095,93096,93097,93098,49108,49109,60040,60041,6653"),
    # 4709 traz populacao e crescimento, mas NAO area nem densidade - essas
    # estao na 4714. A 4712 e sobre domicilios; a situacao urbana/rural do
    # Censo 2022 esta na 9923.
    ("populacao_area_densidade", "4714", "allxp", "last", ""),
    ("populacao_situacao_domicilio_censo2022", "9923", "allxp", "last",
     "c1/allxt"),
    ("domicilios_ocupados_censo2022", "4712", "allxp", "last", ""),
    # 37 PIB · 543 impostos · 498 VA total · 513 agropecuaria · 517 industria
    # · 6575 servicos · 525 administracao. Nao existe variavel de PIB per
    # capita nesta tabela: e calculado no perfil, PIB dividido pela populacao.
    # serie: o VA setorial e publicado depois do PIB total, entao o ultimo
    # ano costuma vir com "..." nos setores
    ("pib_municipal", "5938", "37,543,498,513,517,6575,525", "last%206", ""),
    ("populacao_estimada_serie", "6579", "allxp", "all", ""),

    # Cadastro Central de Empresas (CEMPRE) - serie encerrada em 2021, mas e a
    # unica fonte nacional de emprego e massa salarial por municipio que cobre
    # PR, MS e SC no mesmo metodo. Supre o que o IPARDES da apenas ao Parana.
    ("cempre_emprego_e_salarios", "1685", "706,707,708,662,1606", "all", ""),
    ("cempre_empresas_por_cnae", "993", "2585", "last",
     "c12762/allxt/c319/0/c12386/0"),
]


def buscar(url: str, tentativas: int = 3):
    for i in range(tentativas):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0",
                              "Accept-Encoding": "gzip"})
            resp = urllib.request.urlopen(req, timeout=120)
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return json.loads(raw.decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if i == tentativas - 1:
                raise
            time.sleep(3 * (i + 1))
    return None


def normalizar(dados: list[dict]) -> pd.DataFrame:
    """O SIDRA devolve a 1a linha como dicionario de rotulos das colunas."""
    if not dados or len(dados) < 2:
        return pd.DataFrame()
    rotulos = dados[0]
    linhas = []
    for r in dados[1:]:
        linhas.append({rotulos.get(k, k): v for k, v in r.items()})
    return pd.DataFrame(linhas)


resultados, falhas = {}, []
for rotulo, tabela, variaveis, periodo, classif in TABELAS:
    url = (f"https://apisidra.ibge.gov.br/values/t/{tabela}/n6/{COD}"
           f"/v/{variaveis}/p/{periodo}")
    if classif:
        url += "/" + classif
    try:
        d = normalizar(buscar(url))
        if d.empty:
            falhas.append((rotulo, tabela, "resposta vazia"))
            print(f"  --  {rotulo:<44} tabela {tabela}: vazia")
            continue
        # confere cobertura dos 12
        colmun = next((c for c in d.columns if c.startswith("Município")
                       and "Código" in c), None)
        n = d[colmun].nunique() if colmun else 0
        resultados[rotulo] = d
        print(f"  ok  {rotulo:<44} tabela {tabela}: "
              f"{len(d):>6,} linhas · {n}/12 municípios")
    except Exception as e:
        falhas.append((rotulo, tabela, str(e)[:80]))
        print(f"  ERRO {rotulo:<43} tabela {tabela}: {str(e)[:60]}")

print()
for rotulo, d in resultados.items():
    d.to_csv(DESTINO / f"sidra_{rotulo}.csv", index=False, encoding="utf-8-sig")

if resultados:
    with pd.ExcelWriter(DESTINO / "sidra_base_municipal.xlsx",
                        engine="openpyxl") as w:
        for rotulo, d in resultados.items():
            d.to_excel(w, sheet_name=rotulo[:31], index=False)
        if falhas:
            pd.DataFrame(falhas, columns=["indicador", "tabela", "motivo"]
                         ).to_excel(w, sheet_name="Não coletados", index=False)

# --- procedencia ------------------------------------------------------------
proc = {
    "coletado_em": time.strftime("%Y-%m-%d %H:%M"),
    "fonte": "SIDRA / IBGE — https://apisidra.ibge.gov.br",
    "municipios": {str(m.codigo_ibge): m.nome_uf for m in MUNICIPIOS},
    "tabelas": [{"rotulo": r, "tabela": t, "variaveis": v, "periodo": p,
                 "classificacoes": c, "coletada": r in resultados}
                for r, t, v, p, c in TABELAS],
}
(DESTINO / "procedencia.json").write_text(
    json.dumps(proc, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"Tabelas coletadas: {len(resultados)} de {len(TABELAS)}")
print(f"Gravado em: {DESTINO}")
