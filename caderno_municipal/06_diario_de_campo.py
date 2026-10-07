# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
DIARIO CRONOLOGICO DE CAMPO
================================================================================
Reconstroi a sequencia real do levantamento a partir do carimbo de envio do
Jotform ("Submission Date"), que registra data e hora de cada ficha.

POR QUE IMPORTA
    A ordem em que as fichas foram preenchidas identifica pontos que o nome nao
    identifica. Rotulos como "P1", "P3" ou "Rotatoria" so fazem sentido dentro
    da jornada em que foram usados.

CUIDADO COM O CAMPO "Data"
    O formulario tem tambem um campo "Data", digitado a mao, que diverge do
    carimbo em varios registros (ha ficha de Bonito enviada em 13/08 com "Data"
    de outubro, e uma de Campo Grande com ano 2036). O carimbo de envio e a
    fonte confiavel; o campo "Data" nao.

SAIDA
    02_Dados_Municipais/diario_de_campo.xlsx
    00_Gestao/diario_de_campo.md
================================================================================
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from comum import (  # noqa: E402
    JOTFORM, DIR_DADOS, DIR_GESTAO, MUNICIPIOS, normalizar_municipio,
    parse_data_pt,
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

FORMULARIOS = [
    ("Geral",      "Formulário_Geral_-_Produto_04*", "Município de coleta",
     "Ponto de análise", "Data"),
    ("Rodoviária", "Formulário_Rodoviárias_-_Produt*", "Município", "Nome",
     "Data e horário da visita"),
    ("Aeroporto",  "Formulário_Aeroportos_-_Produto*", "Município",
     "Nome do aeroporto", "Data e horário da visita"),
    ("Aduana",     "Formulário_Aduanas_-_Produto_04*", "Município",
     "Nome da aduana", "Data e horário da visita"),
]


def ler(padrao: str) -> pd.DataFrame:
    """Prefere o export .xlsx mais recente; cai para o .csv se nao houver."""
    xs = sorted(JOTFORM.glob(padrao + ".xlsx"))
    if xs:
        return pd.read_excel(xs[-1])
    cs = sorted(JOTFORM.glob(padrao + ".csv"))
    for enc in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(cs[-1], encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(padrao)


linhas = []
for rotulo, padrao, col_mun, col_nome, col_data in FORMULARIOS:
    df = ler(padrao)
    for _, r in df.iterrows():
        mun = normalizar_municipio(r[col_mun])
        linhas.append({
            "enviado_em": parse_data_pt(r.get("Submission Date")),
            "formulário": rotulo,
            "município": mun.nome_uf if mun else str(r[col_mun]),
            "cod_ibge": mun.codigo_ibge if mun else pd.NA,
            "ponto": r[col_nome],
            "data_declarada": parse_data_pt(r.get(col_data)),
        })

D = pd.DataFrame(linhas)
ok = D.enviado_em.notna()
print(f"Carimbo de envio lido em {ok.sum()} de {len(D)} fichas "
      f"({ok.mean()*100:.0f}%)")

# --- divergencia entre o carimbo e a data digitada --------------------------
amb = D[D.enviado_em.notna() & D.data_declarada.notna()].copy()
amb["dias"] = (amb.data_declarada - amb.enviado_em).dt.days.abs()
suspeitas = amb[amb.dias > 15]
print(f"Fichas em que a 'Data' digitada diverge do envio em mais de 15 dias: "
      f"{len(suspeitas)} de {len(amb)}")

D = D.sort_values("enviado_em")

# ==============================================================================
# RELATORIO
# ==============================================================================
print("\n" + "=" * 92)
print("DIÁRIO DE CAMPO — ordem real de preenchimento")
print("=" * 92)

md = ["# Diário de campo — sequência real do levantamento", "",
      "Reconstruído a partir do carimbo de envio do Jotform "
      "(`Submission Date`), gerado por `caderno_municipal/06_diario_de_campo.py`.", "",
      "> O campo **Data**, digitado em campo, diverge do carimbo em vários "
      "registros e não deve ser usado como referência temporal.", "", "---", ""]

for m in MUNICIPIOS:
    sub = D[D.cod_ibge == m.codigo_ibge]
    if sub.empty:
        continue
    print(f"\n--- {m.nome_uf} ---")
    md += [f"## {m.nome_uf}", "",
           "| Enviado em | Formulário | Ponto |", "| :--- | :--- | :--- |"]
    for _, r in sub.iterrows():
        q = r.enviado_em.strftime("%d/%m/%Y %H:%M") if pd.notna(r.enviado_em) else "—"
        print(f"   {q:<17} [{r['formulário']:<10}] {str(r['ponto'])[:56]}")
        md.append(f"| {q} | {r['formulário']} | {str(r['ponto'])} |")
    md.append("")

if len(suspeitas):
    md += ["---", "", "## Divergências entre o carimbo de envio e a data digitada",
           "", "| Município | Ponto | Enviado em | 'Data' digitada | Diferença |",
           "| :--- | :--- | :--- | :--- | :-: |"]
    for _, r in suspeitas.sort_values("dias", ascending=False).iterrows():
        md.append(f"| {r['município']} | {str(r['ponto'])[:40]} | "
                  f"{r.enviado_em:%d/%m/%Y} | {r.data_declarada:%d/%m/%Y} | "
                  f"{int(r.dias)} dias |")

(DIR_GESTAO / "diario_de_campo.md").write_text("\n".join(md) + "\n",
                                               encoding="utf-8")
with pd.ExcelWriter(DIR_DADOS / "diario_de_campo.xlsx", engine="openpyxl") as w:
    D.to_excel(w, sheet_name="Diário", index=False)
    if len(suspeitas):
        suspeitas.to_excel(w, sheet_name="Datas divergentes", index=False)

print(f"\nDiário: {DIR_GESTAO / 'diario_de_campo.md'}")
