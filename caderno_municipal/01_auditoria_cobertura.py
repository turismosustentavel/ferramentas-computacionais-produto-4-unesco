# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
FASE 1 - AUDITORIA DE COBERTURA DOS DADOS
================================================================================
OBJETIVO:
    Responder, para cada um dos 12 municipios, o que existe e o que falta em
    cada fonte do acervo. O resultado orienta o levantamento complementar e
    documenta as lacunas de informacao de cada municipio.

PRINCIPIO:
    Ausencia de dado nao e omissao - e achado. Tudo que falta e registrado
    explicitamente, com a fonte que deveria te-lo.

SAIDAS:
    00_Gestao/auditoria_cobertura.xlsx   - matriz municipio x fonte
    00_Gestao/auditoria_cobertura.md     - lacunas por municipio
================================================================================
"""
from __future__ import annotations

import io
import json
import sys
from collections import Counter, defaultdict

import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from comum import (  # noqa: E402
    MUNICIPIOS, POR_CODIGO, ACERVO, ENTREGAS, JOTFORM, CAMPO, CAMADAS_QGIS,
    DIR_GESTAO, PRODUCAO, normalizar_municipio,
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Acumulador: {codigo_ibge: {nome_da_metrica: valor}}
cobertura: dict[int, dict[str, object]] = {m.codigo_ibge: {} for m in MUNICIPIOS}
# Registro de grafias nao reconhecidas, por fonte
orfaos: dict[str, Counter] = defaultdict(Counter)
# Notas de execucao (fontes ausentes, erros de leitura)
notas: list[str] = []


def _contar(fonte: str, valores, rotulo: str) -> None:
    """Normaliza uma sequencia de nomes e acumula a contagem por municipio."""
    c = Counter()
    for v in valores:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            continue
        m = normalizar_municipio(v)
        if m is None:
            orfaos[fonte][str(v).strip()] += 1
        else:
            c[m.codigo_ibge] += 1
    for cod in cobertura:
        cobertura[cod][rotulo] = c.get(cod, 0)


def _ler_csv(caminho):
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(caminho, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"nao foi possivel ler {caminho}")


print("=" * 78)
print("AUDITORIA DE COBERTURA - CADERNO POR MUNICIPIO")
print("=" * 78)

# ==============================================================================
# 1. FORMULARIOS DE CAMPO (Jotform)
# ==============================================================================
print("\n[1] Formularios de campo")
FORMULARIOS = [
    ("Formulário_Geral_-_Produto_04*.csv",  "Município de coleta", "Fichas: pontos gerais"),
    ("Formulário_Rodoviárias_-_Produt*.csv", "Município",          "Fichas: rodoviárias"),
    ("Formulário_Aeroportos_-_Produto*.csv", "Município",          "Fichas: aeroportos"),
    ("Formulário_Aduanas_-_Produto_04*.csv", "Município",          "Fichas: aduanas"),
]
for padrao, coluna, rotulo in FORMULARIOS:
    arquivos = sorted(JOTFORM.glob(padrao))
    if not arquivos:
        notas.append(f"Formulário não encontrado: {padrao}")
        for cod in cobertura:
            cobertura[cod][rotulo] = 0
        continue
    df = _ler_csv(arquivos[0])
    _contar(rotulo, df[coluna], rotulo)
    print(f"    {rotulo:<28} {len(df):>4} registros  ({arquivos[0].name})")

# ==============================================================================
# 2. PONTOS DE AFERICAO SELECIONADOS (fonte de verdade)
# ==============================================================================
print("\n[2] Pontos de aferição selecionados")
csv_pontos = CAMPO / "03_Pontos_Afericao" / "pontos_afericao_selecionados.csv"
if csv_pontos.exists():
    dfp = _ler_csv(csv_pontos)
    _contar("Pontos selecionados", dfp["municipio"], "Pontos de aferição selecionados")
    print(f"    {len(dfp)} pontos em {dfp['municipio'].nunique()} municípios")
else:
    notas.append(f"Ausente: {csv_pontos}")
    for cod in cobertura:
        cobertura[cod]["Pontos de aferição selecionados"] = 0

# ==============================================================================
# 3. CAMADAS DA SELECAO DOS PONTOS
# ==============================================================================
print("\n[3] Camadas da seleção dos pontos")
CAMADAS = [
    ("1_pontos_afericao_selecionados", "Camada SIG: pontos de aferição"),
    ("2_pontos_sobreposicao_fluxos",   "Camada SIG: sobreposição de fluxos"),
    ("3_manchas_fluxo_rotas",          "Camada SIG: vértices de rotas"),
    ("4_atrativos_turisticos",         "Camada SIG: atrativos"),
]
for arq, rotulo in CAMADAS:
    p = CAMADAS_QGIS / f"{arq}.geojson"
    if not p.exists():
        notas.append(f"Ausente: {p}")
        for cod in cobertura:
            cobertura[cod][rotulo] = 0
        continue
    g = json.loads(p.read_text(encoding="utf-8"))
    _contar(rotulo, (f["properties"].get("MUNICIPIO") for f in g["features"]), rotulo)
    print(f"    {rotulo:<38} {len(g['features']):>6} feições")

# ==============================================================================
# 4. ACERVO FOTOGRAFICO DE CAMPO
# ==============================================================================
print("\n[4] Acervo fotográfico")
EXT_FOTO = {".jpg", ".jpeg", ".heic", ".png", ".dng", ".tif"}
EXT_VIDEO = {".mp4", ".mov", ".avi"}
for m in MUNICIPIOS:
    d = m.dir_fotos
    if not d.exists():
        cobertura[m.codigo_ibge]["Fotografias"] = 0
        cobertura[m.codigo_ibge]["Vídeos"] = 0
        notas.append(f"Pasta de fotos ausente: {d}")
        continue
    arqs = [a for a in d.iterdir() if a.is_file()]
    cobertura[m.codigo_ibge]["Fotografias"] = sum(
        1 for a in arqs if a.suffix.lower() in EXT_FOTO)
    cobertura[m.codigo_ibge]["Vídeos"] = sum(
        1 for a in arqs if a.suffix.lower() in EXT_VIDEO)
print(f"    {sum(cobertura[m.codigo_ibge]['Fotografias'] for m in MUNICIPIOS)} fotografias no total")

# ==============================================================================
# 5. FICHAS DE CAMPO EM WORD
# ==============================================================================
print("\n[5] Fichas de campo (DOCX)")
for m in MUNICIPIOS:
    d = CAMPO / "02_Fichas_Preenchidas" / m.pasta_campo
    n = len(list(d.glob("*.docx"))) if d.exists() else 0
    if n == 0:
        d2 = ENTREGAS / "Entrega 4.3" / m.pasta_campo / "Documentos_e_Anotacoes"
        n = len(list(d2.glob("*.docx"))) if d2.exists() else 0
    cobertura[m.codigo_ibge]["Fichas DOCX"] = n

# ==============================================================================
# 6. ENTREVISTAS COM SECRETARIAS MUNICIPAIS
# ==============================================================================
print("\n[6] Entrevistas com secretarias")
dir_ent = ACERVO / "04_Entrevistas_e_Qualitativo" / "Entrevistas_Municipais"
achados_ent: Counter = Counter()
if dir_ent.exists():
    for arq in dir_ent.rglob("*"):
        if arq.suffix.lower() not in {".docx", ".md", ".pdf"}:
            continue
        mm = normalizar_municipio(arq.stem.split("-")[-1])
        if mm is None:
            for cand in MUNICIPIOS:
                if cand.nome.lower() in arq.stem.lower():
                    mm = cand
                    break
        if mm:
            achados_ent[mm.codigo_ibge] += 1
else:
    notas.append(f"Ausente: {dir_ent}")
for cod in cobertura:
    cobertura[cod]["Entrevista secretaria"] = achados_ent.get(cod, 0)

# ==============================================================================
# 7. ESTUDO QUALITATIVO DE RELEVANCIA DOS ATRATIVOS
# ==============================================================================
print("\n[7] Estudo de relevância dos atrativos")
md_relev = PRODUCAO / "Seleção dos pontos para aferição" / "Atrativos_Relevantes_Por_Cidade.md"
texto_relev = md_relev.read_text(encoding="utf-8") if md_relev.exists() else ""
if not texto_relev:
    notas.append(f"Ausente: {md_relev}")
for m in MUNICIPIOS:
    cobertura[m.codigo_ibge]["Estudo de relevância"] = int(
        f"### 2." in texto_relev and m.nome in texto_relev)

# ==============================================================================
# 8. CHECKLISTS NAUTICOS IN LOCO
# ==============================================================================
print("\n[8] Checklists náuticos")
dir_naut = ACERVO / "08_Infraestrutura_e_Turismo_Nautico" / "03_Checklists_e_Fichas_Municipais"
naut: Counter = Counter()
if dir_naut.exists():
    for arq in dir_naut.rglob("*"):
        if arq.suffix.lower() not in {".docx", ".pdf"}:
            continue
        for cand in MUNICIPIOS:
            if cand.nome.lower() in arq.stem.lower():
                naut[cand.codigo_ibge] += 1
                break
else:
    notas.append(f"Ausente: {dir_naut}")
for cod in cobertura:
    cobertura[cod]["Checklist náutico"] = naut.get(cod, 0)

# ==============================================================================
# 9. MONTAGEM DA MATRIZ
# ==============================================================================
linhas = []
for m in MUNICIPIOS:
    linha = {
        "Ordem": m.ordem,
        "Código IBGE": m.codigo_ibge,
        "Município": m.nome,
        "UF": m.uf,
        "Região imediata": m.reg_imediata,
        "Região intermediária": m.reg_intermediaria,
    }
    linha.update(cobertura[m.codigo_ibge])
    linhas.append(linha)
matriz = pd.DataFrame(linhas).sort_values("Ordem")

DIR_GESTAO.mkdir(parents=True, exist_ok=True)
xlsx = DIR_GESTAO / "auditoria_cobertura.xlsx"
with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
    matriz.to_excel(w, sheet_name="Cobertura", index=False)
    if orfaos:
        pd.DataFrame(
            [{"Fonte": f, "Grafia não reconhecida": g, "Ocorrências": n}
             for f, c in orfaos.items() for g, n in c.most_common()]
        ).to_excel(w, sheet_name="Grafias órfãs", index=False)
    if notas:
        pd.DataFrame({"Nota": notas}).to_excel(w, sheet_name="Notas", index=False)

# ==============================================================================
# 10. RELATORIO NA TELA
# ==============================================================================
print("\n" + "=" * 78)
print("MATRIZ DE COBERTURA")
print("=" * 78)
colunas_exibir = [c for c in matriz.columns
                  if c not in ("Ordem", "Código IBGE", "UF",
                               "Região imediata", "Região intermediária")]
with pd.option_context("display.width", 250, "display.max_columns", 40):
    print(matriz[colunas_exibir].to_string(index=False))

if orfaos:
    print("\n" + "-" * 78)
    print("GRAFIAS NÃO RECONHECIDAS (precisam entrar no dicionário de aliases)")
    print("-" * 78)
    for fonte, c in orfaos.items():
        for g, n in c.most_common():
            print(f"  [{fonte}] {g!r} ({n}x)")
else:
    print("\nNenhuma grafia órfã — o dicionário canônico cobre todas as fontes lidas.")

if notas:
    print("\n" + "-" * 78)
    print("NOTAS DE EXECUÇÃO")
    print("-" * 78)
    for n in notas:
        print(f"  · {n}")

print(f"\nMatriz gravada em: {xlsx}")

# ==============================================================================
# 11. LACUNAS POR MUNICIPIO
# ==============================================================================
# Cada item traz: rotulo da coluna -> (descricao, predicado de pertinencia).
# O predicado evita acusar como lacuna aquilo que simplesmente nao se aplica:
# nao ha "ficha de aeroporto faltando" em municipio sem aerodromo.
CRITICAS = {
    "Fichas: aduanas": (
        "ficha de aduana — o município faz divisa internacional com {pais}",
        lambda m: m.linha_internacional),
    "Fichas: aeroportos": (
        "ficha de aeroporto — o município tem aeródromo com operação de passageiros",
        lambda m: m.tem_aerodromo),
    "Checklist náutico": (
        "checklist de infraestrutura náutica — o município tem corpo d'água navegável",
        lambda m: m.agua_navegavel),
    "Estudo de relevância": (
        "estudo qualitativo de relevância dos atrativos",
        lambda m: True),
    "Entrevista secretaria": (
        "entrevista com a secretaria municipal de turismo",
        lambda m: True),
}

linhas_md: list[str] = [
    "# Auditoria de Cobertura de Dados — Caderno por Município",
    "",
    "**Produto 4 · Projeto UNESCO UNES 2369/2025 · Itaipu Parquetec — TS.DTUR**  ",
    "Gerado por `caderno_municipal/01_auditoria_cobertura.py` — não editar à mão.",
    "",
    "Este documento responde, fonte a fonte, o que cada município tem e o que lhe falta. ",
    "Cada ausência registrada aqui é uma lacuna de informação do município. ",
    "Ausência de dado é achado, não omissão.",
    "",
    "---",
    "",
    "## 1. Matriz de cobertura",
    "",
]

cabec = ["Município"] + colunas_exibir[1:]
linhas_md.append("| " + " | ".join(cabec) + " |")
linhas_md.append("| :--- " + "| :-: " * (len(cabec) - 1) + "|")
for _, r in matriz.iterrows():
    linhas_md.append("| " + " | ".join(str(r[c]) for c in cabec) + " |")

# --- Deficit entre pontos selecionados e fichas efetivamente preenchidas -----
linhas_md += [
    "",
    "---",
    "",
    "## 2. Déficit de levantamento in loco",
    "",
    "Diferença entre os pontos de aferição **selecionados** (fonte de verdade: ",
    "`pontos_afericao_selecionados.csv`) e as fichas do Formulário Geral **efetivamente ",
    "preenchidas** em campo.",
    "",
    "| Município | Selecionados | Fichas preenchidas | Déficit | Cobertura |",
    "| :--- | :-: | :-: | :-: | :-: |",
]
tot_sel = tot_fic = 0
for _, r in matriz.iterrows():
    sel = int(r["Pontos de aferição selecionados"])
    fic = int(r["Fichas: pontos gerais"])
    tot_sel += sel
    tot_fic += fic
    pct = f"{fic / sel * 100:.0f}%" if sel else "—"
    linhas_md.append(
        f"| {r['Município']} | {sel} | {fic} | **{sel - fic}** | {pct} |")
pct_tot = f"{tot_fic / tot_sel * 100:.0f}%" if tot_sel else "—"
linhas_md.append(
    f"| **Total** | **{tot_sel}** | **{tot_fic}** | **{tot_sel - tot_fic}** | "
    f"**{pct_tot}** |")

# --- Ausencias por municipio -------------------------------------------------
linhas_md += ["", "---", "", "## 3. Ausências por município", ""]
for _, r in matriz.iterrows():
    m = POR_CODIGO[int(r["Código IBGE"])]
    faltas: list[str] = []
    nao_se_aplica: list[str] = []

    for col, (desc, pertinente) in CRITICAS.items():
        if col not in matriz.columns:
            continue
        texto = desc.format(pais=m.pais_vizinho or "—")
        if not pertinente(m):
            nao_se_aplica.append(texto.split(" — ")[0])
        elif int(r[col]) == 0:
            faltas.append(texto)

    sel = int(r["Pontos de aferição selecionados"])
    fic = int(r["Fichas: pontos gerais"])
    if sel - fic > 0:
        faltas.append(
            f"{sel - fic} de {sel} ponto(s) de aferição selecionado(s) sem ficha de "
            f"campo correspondente")
    camada = int(r["Camada SIG: pontos de aferição"])
    if camada < sel:
        faltas.append(
            f"camada SIG de pontos de aferição desatualizada: {camada} feição(ões) "
            f"contra {sel} ponto(s) no CSV oficial")

    linhas_md.append(f"### {r['Município']} ({r['UF']})")
    linhas_md.append("")
    if faltas:
        linhas_md.append("**Lacunas:**")
        linhas_md.append("")
        linhas_md += [f"- {f}" for f in faltas]
    else:
        linhas_md.append("Sem lacunas entre as fontes auditadas.")
    if nao_se_aplica:
        linhas_md.append("")
        linhas_md.append("*Não se aplica: " + "; ".join(nao_se_aplica) + ".*")
    linhas_md.append("")

if notas:
    linhas_md += ["---", "", "## 4. Notas de execução", ""]
    linhas_md += [f"- {n}" for n in notas]

md = DIR_GESTAO / "auditoria_cobertura.md"
md.write_text("\n".join(linhas_md) + "\n", encoding="utf-8")
print(f"Lacunas por município gravadas em: {md}")
