# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
EMPREGO FORMAL NO TURISMO - RAIS 2025 (MTur)
================================================================================
O conjunto "Empregos Formais no Turismo" do MTur publica a RAIS em nivel de
VINCULO: 2,39 milhoes de linhas, uma por trabalhador. E a melhor fonte de
emprego turistico municipal que existe - nacional, recente e ja classificada
por Atividade Caracteristica do Turismo.

Duas particularidades exigiram tratamento proprio:
  1. O arquivo e um .zip de 57 MB rotulado como CSV no portal;
  2. O separador e virgula, nao ponto-e-virgula como nos demais conjuntos.

A chave de municipio aqui e `Municipio_Codigo`, o codigo IBGE de 6 digitos -
mais confiavel que o nome, que traria homonimos entre estados.

O caderno nao usa o vinculo individual: usa agregados por municipio. Este
script le em blocos, filtra os 12 municipios e produz os recortes analiticos.

SAIDA
    09_Base_Socioeconomica_Municipal/08_MTur_Dados_Abertos/rais_turismo/
================================================================================
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from comum import ACERVO, MUNICIPIOS, POR_CODIGO  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = ACERVO / "09_Base_Socioeconomica_Municipal" / "08_MTur_Dados_Abertos"
SAIDA = BASE / "rais_turismo"
SAIDA.mkdir(parents=True, exist_ok=True)

zips = list((BASE / "nacional").glob("empregos_formais_turismo*"))
if not zips:
    print("Arquivo da RAIS não encontrado. Rode antes o script 10.")
    sys.exit(1)

z = zipfile.ZipFile(zips[0])
interno = max((n for n in z.namelist() if n.lower().endswith(".csv")),
              key=lambda n: z.getinfo(n).file_size)
print(f"Lendo {interno} de {zips[0].name}")

# codigo IBGE de 6 digitos = os 7 digitos sem o verificador
COD6 = {str(m.codigo_ibge)[:6]: m for m in MUNICIPIOS}

blocos, total = [], 0
with z.open(interno) as fh:
    leitor = pd.read_csv(fh, sep=",", dtype=str, chunksize=200_000,
                         encoding="latin-1", on_bad_lines="skip")
    for bloco in leitor:
        total += len(bloco)
        sub = bloco[bloco["Municipio_Codigo"].isin(COD6)]
        if not sub.empty:
            blocos.append(sub)

if not blocos:
    print("Nenhum vínculo dos municípios do estudo encontrado.")
    sys.exit(1)

D = pd.concat(blocos, ignore_index=True)
D["codigo_ibge"] = D["Municipio_Codigo"].map(lambda c: COD6[c].codigo_ibge)
D["municipio"] = D["Municipio_Codigo"].map(lambda c: COD6[c].nome)
D["uf"] = D["Municipio_Codigo"].map(lambda c: COD6[c].uf)
D["remuneracao"] = pd.to_numeric(D["Remuneracao_Dezembro"], errors="coerce")

print(f"\nVínculos lidos: {total:,} · nos 12 municípios: {len(D):,}")

D.to_csv(SAIDA / "rais_turismo_2025_vinculos_12_municipios.csv",
         index=False, encoding="utf-8-sig")

# ==============================================================================
# AGREGADOS PARA O CADERNO
# ==============================================================================
def agrega(por: list[str], nome: str) -> pd.DataFrame:
    g = (D.groupby(["codigo_ibge", "municipio", "uf"] + por)
           .agg(vinculos=("Id", "size"),
                remuneracao_media=("remuneracao", "mean"),
                remuneracao_mediana=("remuneracao", "median"))
           .round(2).reset_index())
    g.to_csv(SAIDA / f"rais_turismo_2025_{nome}.csv", index=False,
             encoding="utf-8-sig")
    return g

total_mun = agrega([], "por_municipio")
por_act = agrega(["ACT"], "por_act")
por_sexo = agrega(["Sexo"], "por_sexo")
agrega(["Escolaridade_Rotulo"], "por_escolaridade")
agrega(["Faixa_Etaria", "Idade_Rotulo"], "por_faixa_etaria")

print("\nVÍNCULOS FORMAIS NO TURISMO POR MUNICÍPIO — RAIS 2025")
t = total_mun.sort_values("vinculos", ascending=False)
for _, r in t.iterrows():
    print(f"  {r['municipio'] + ' (' + r['uf'] + ')':<26} "
          f"{int(r['vinculos']):>7,} vínculos · "
          f"remuneração média R$ {r['remuneracao_media']:>9,.2f}")

print("\nCOMPOSIÇÃO POR ATIVIDADE CARACTERÍSTICA DO TURISMO")
p = por_act.pivot_table(index="ACT", columns="municipio", values="vinculos",
                        aggfunc="sum", fill_value=0)
p["TOTAL"] = p.sum(axis=1)
print(p[["TOTAL"]].sort_values("TOTAL", ascending=False).to_string())

with pd.ExcelWriter(SAIDA / "rais_turismo_2025_agregados.xlsx",
                    engine="openpyxl") as w:
    total_mun.to_excel(w, sheet_name="Por município", index=False)
    por_act.to_excel(w, sheet_name="Por ACT", index=False)
    por_sexo.to_excel(w, sheet_name="Por sexo", index=False)

print(f"\nGravado em: {SAIDA}")
