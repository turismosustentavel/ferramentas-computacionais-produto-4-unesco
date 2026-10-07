# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
EXTRACAO DA BASE IPARDES PARA OS MUNICIPIOS DO ESTUDO
================================================================================
O IPARDES publica series municipais do Parana em planilhas largas: UTF-16,
separadas por tabulacao, com TRES linhas de cabecalho -

    linha 0   grupo do indicador      "Populacao Censitaria"
    linha 1   subindicador            "Total" | "Menores de 1 ano" | ...
    linha 2   recorte da coluna       "2000" | "2010" | "2022"
    linha 3+  municipios              "Foz do Iguacu" | "Medianeira" | ...
    coluna 0  Municipio/Estado
    coluna 1  Regiao a que Pertence

Este script reduz tudo isso a formato longo - municipio, indicador,
subindicador, recorte, valor - e filtra os municipios do estudo.

LIMITE DA FONTE
    O IPARDES cobre apenas o Parana. Dos 12 municipios do caderno, atende 5:
    Foz do Iguacu, Medianeira, Capanema, Barracao e Guaira. Mato Grosso do Sul
    e Santa Catarina precisam de fonte nacional equivalente (script 09).

SAIDA
    09_Base_Socioeconomica_Municipal/02_Extracoes_12_municipios/
        ipardes_series_longas_municipios_estudo.csv / .xlsx
================================================================================
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from comum import ACERVO, MUNICIPIOS, normalizar_municipio  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = ACERVO / "09_Base_Socioeconomica_Municipal"
ORIGEM = BASE / "01_IPARDES_PR_bruto"
DESTINO = BASE / "02_Extracoes_12_municipios"
DESTINO.mkdir(parents=True, exist_ok=True)


def ler_ipardes(caminho: Path) -> pd.DataFrame | None:
    """Le uma planilha do IPARDES e devolve o formato longo."""
    bruto = None
    for enc in ("utf-16", "utf-16-le", "utf-8-sig", "latin-1"):
        try:
            t = pd.read_csv(caminho, encoding=enc, sep="\t", header=None,
                            dtype=str, engine="python")
            if t.shape[1] > 1:
                bruto = t
                break
        except Exception:
            continue
    if bruto is None or bruto.shape[0] < 4:
        return None

    # Localiza a linha de cabecalho que nomeia a coluna de municipio.
    linha_cab = None
    for i in range(min(6, len(bruto))):
        if str(bruto.iat[i, 0]).strip().lower().startswith("munic"):
            linha_cab = i
            break
    if linha_cab is None:
        return None

    grupo = bruto.iloc[max(0, linha_cab - 2)].ffill()
    sub = bruto.iloc[max(0, linha_cab - 1)].ffill()
    recorte = bruto.iloc[linha_cab]
    dados = bruto.iloc[linha_cab + 1:].copy()

    registros = []
    for _, r in dados.iterrows():
        nome = str(r.iloc[0]).strip()
        m = normalizar_municipio(nome)
        if m is None:
            continue
        for c in range(2, bruto.shape[1]):
            valor = r.iloc[c]
            if valor is None or str(valor).strip() in ("", "nan", "-", "..."):
                continue
            registros.append({
                "codigo_ibge": m.codigo_ibge,
                "municipio": m.nome,
                "uf": m.uf,
                "regiao_ipardes": str(r.iloc[1]).strip(),
                "arquivo": caminho.name,
                "tema": caminho.parent.name,
                "indicador": str(grupo.iloc[c]).strip(),
                "subindicador": str(sub.iloc[c]).strip(),
                "recorte": str(recorte.iloc[c]).strip(),
                "valor_bruto": str(valor).strip(),
            })
    return pd.DataFrame(registros) if registros else None


def para_numero(s: str):
    """Converte o formato brasileiro do IPARDES em numero."""
    t = str(s).replace(".", "").replace(",", ".").strip()
    try:
        return float(t)
    except ValueError:
        return None


arquivos = sorted(ORIGEM.rglob("*.csv"))
print(f"Planilhas do IPARDES encontradas: {len(arquivos)}\n")

partes, falhas = [], []
for a in arquivos:
    try:
        d = ler_ipardes(a)
    except Exception as e:
        falhas.append((a.name, str(e)[:70]))
        continue
    if d is None or d.empty:
        falhas.append((a.name, "sem municípios do estudo ou layout não reconhecido"))
    else:
        partes.append(d)

if not partes:
    print("Nenhuma série extraída."); sys.exit(1)

L = pd.concat(partes, ignore_index=True)
L["valor"] = L.valor_bruto.map(para_numero)

print(f"Séries extraídas: {len(L):,} linhas")
print(f"Planilhas aproveitadas: {len(partes)} · sem aproveitamento: {len(falhas)}")
print(f"Municípios atendidos: {L.municipio.nunique()} — "
      f"{', '.join(sorted(L.municipio.unique()))}")

print("\nPOR TEMA")
print(L.groupby("tema").agg(linhas=("valor", "size"),
                            indicadores=("indicador", "nunique")).to_string())

print("\nINDICADORES COM MAIS SÉRIES")
print(L.indicador.value_counts().head(18).to_string())

L.to_csv(DESTINO / "ipardes_series_longas_municipios_estudo.csv",
         index=False, encoding="utf-8-sig")
with pd.ExcelWriter(DESTINO / "ipardes_series_longas_municipios_estudo.xlsx",
                    engine="openpyxl") as w:
    L.to_excel(w, sheet_name="Séries", index=False)
    L.groupby(["tema", "indicador"]).size().reset_index(
        name="linhas").to_excel(w, sheet_name="Índice", index=False)
    if falhas:
        pd.DataFrame(falhas, columns=["arquivo", "motivo"]).to_excel(
            w, sheet_name="Não aproveitados", index=False)

print(f"\nGravado em: {DESTINO}")
