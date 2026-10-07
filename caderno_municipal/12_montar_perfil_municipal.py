# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
FASE 1d - PERFIL MUNICIPAL CONSOLIDADO
================================================================================
Reune, num arquivo por municipio, tudo o que a Fase 1 estabeleceu:

    identificacao      registro canonico, codigo IBGE validado, regioes do IBGE
    turismo            regiao turistica e IGR (MTur), categorizacao A-E
    demografia         populacao, area, densidade, urbano/rural, piramide etaria
    economia           PIB, valor adicionado por setor, emprego e massa salarial
    turismo_trabalho   vinculos formais no turismo por ACT e por sexo (RAIS 2025)
    oferta             prestadores CADASTUR por categoria
    campo              pontos de afericao, fichas vinculadas, fotografias
    lacunas            o que falta e por que

PRINCIPIO
    Cada valor carrega a fonte. Onde a fonte nao cobre o municipio, o campo
    registra a ausencia explicitamente em vez de ficar vazio, o que permite
    listar as lacunas de cada municipio diretamente do perfil.

SAIDA
    02_Dados_Municipais/<slug>/perfil_municipal.json
    02_Dados_Municipais/perfis_municipais.xlsx   (visao comparativa)
================================================================================
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from comum import (  # noqa: E402
    ACERVO, CAMPO, DIR_DADOS, DIR_GESTAO, MUNICIPIOS,
)

# Pontos que constavam do plano de campo e nao foram aferidos
# (fixado no acervo por `32_pontos_planejados_sem_coleta.py`).
_ARQ_SEM_COLETA = (CAMPO / "03_Pontos_Afericao" /
                   "pontos_planejados_sem_coleta.json")
SEM_COLETA = (json.loads(_ARQ_SEM_COLETA.read_text(encoding="utf-8"))
              ["por_municipio"] if _ARQ_SEM_COLETA.exists() else {})

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = ACERVO / "09_Base_Socioeconomica_Municipal"
SIDRA = BASE / "03_IBGE_SIDRA"
MTUR = BASE / "08_MTur_Dados_Abertos"


def ler(caminho: Path, **kw) -> pd.DataFrame:
    if not caminho.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(caminho, dtype=str, **kw)
    except Exception:
        return pd.DataFrame()


def num(v):
    """SIDRA usa '...', '-' e '..' para indisponivel."""
    if v is None or str(v).strip() in ("", "...", "..", "-", "X", "nan"):
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


# ==============================================================================
# FONTES
# ==============================================================================
pop = ler(SIDRA / "sidra_populacao_area_densidade_censo2022.csv")   # tab. 4709
area = ler(SIDRA / "sidra_populacao_area_densidade.csv")            # tab. 4714
pir = ler(SIDRA / "sidra_populacao_sexo_idade_censo2022.csv")
sit = ler(SIDRA / "sidra_populacao_situacao_domicilio_censo2022.csv")  # 9923
pib = ler(SIDRA / "sidra_pib_municipal.csv")
dom = ler(SIDRA / "sidra_domicilios_ocupados_censo2022.csv")
cem = ler(SIDRA / "sidra_cempre_emprego_e_salarios.csv")

mapa = ler(MTUR / "recorte_12" / "mapa_do_turismo.csv")
categ = ler(MTUR / "recorte_12" / "categorizacao_municipios.csv")
rais_mun = ler(MTUR / "rais_turismo" / "rais_turismo_2025_por_municipio.csv")
rais_act = ler(MTUR / "rais_turismo" / "rais_turismo_2025_por_act.csv")
rais_sexo = ler(MTUR / "rais_turismo" / "rais_turismo_2025_por_sexo.csv")

vinculo = pd.DataFrame()
p_vinc = DIR_DADOS / "vinculo_fichas_pontos.xlsx"
if p_vinc.exists():
    vinculo = pd.read_excel(p_vinc, sheet_name="Vínculo")

cobertura = pd.DataFrame()
p_cob = DIR_GESTAO / "auditoria_cobertura.xlsx"   # gravado pelo 01
if p_cob.exists():
    cobertura = pd.read_excel(p_cob, sheet_name="Cobertura")


def sidra_val(df: pd.DataFrame, cod: int, contem: str):
    """Extrai um valor do formato longo do SIDRA pelo nome da variável."""
    if df.empty:
        return None
    cm = next((c for c in df.columns if c.startswith("Município (Código)")), None)
    cv = next((c for c in df.columns if c.strip() == "Variável"), None)
    if cm is None or cv is None:
        return None
    sub = df[(df[cm] == str(cod)) &
             df[cv].astype(str).str.contains(contem, case=False, na=False)]
    return num(sub["Valor"].iloc[0]) if len(sub) else None


def mtur_campo(df: pd.DataFrame, cod: int, *nomes: str):
    if df.empty:
        return None
    sub = df[df["codigo_ibge"].astype(str) == str(cod)]
    if sub.empty:
        return None
    for n in nomes:
        for c in sub.columns:
            if c.strip().upper() == n.upper():
                v = sub[c].iloc[0]
                return None if pd.isna(v) else str(v).strip()
    return None


# contagem do CADASTUR por categoria
cadastur = {}
for arq in sorted((MTUR / "recorte_12").glob("cadastur_*.csv")):
    d = ler(arq)
    if d.empty or "codigo_ibge" not in d.columns:
        continue
    cadastur[arq.stem.replace("cadastur_", "")] = (
        d.codigo_ibge.astype(str).value_counts().to_dict())

# ==============================================================================
# MONTAGEM
# ==============================================================================
perfis, linhas_comparativo = [], []

def sidra_ultimo(df: pd.DataFrame, cod: int, contem: str):
    """(valor, ano) do ano mais recente com dado publicado.

    Series com varios anos (CEMPRE, PIB) nao podem ser lidas pela primeira
    linha: era assim que o perfil pegava as unidades locais de 2006. E o SIDRA
    marca com '...' o que ainda nao foi publicado (VA setorial de 2023).
    """
    if df.empty:
        return None, None
    cm = next((c for c in df.columns if c.startswith("Município (Código)")), None)
    cv = next((c for c in df.columns if c.strip() == "Variável"), None)
    ca = next((c for c in df.columns if c.strip() == "Ano"), None)
    if cm is None or cv is None:
        return None, None
    sub = df[(df[cm] == str(cod)) &
             df[cv].astype(str).str.contains(contem, case=False, na=False)].copy()
    sub["_v"] = sub["Valor"].map(num)
    sub = sub.dropna(subset=["_v"])
    if sub.empty:
        return None, None
    if ca:
        sub = sub.sort_values(ca)
    return sub["_v"].iloc[-1], (str(sub[ca].iloc[-1]) if ca else None)


def sidra_serie(df: pd.DataFrame, cod: int, contem: str) -> dict:
    """{ano: valor} de todos os anos publicados da variavel."""
    if df.empty:
        return {}
    cm = next((c for c in df.columns if c.startswith("Município (Código)")), None)
    cv = next((c for c in df.columns if c.strip() == "Variável"), None)
    ca = next((c for c in df.columns if c.strip() == "Ano"), None)
    if cm is None or cv is None or ca is None:
        return {}
    sub = df[(df[cm] == str(cod)) &
             df[cv].astype(str).str.contains(contem, case=False, na=False)]
    return {str(a): num(v) for a, v in zip(sub[ca], sub["Valor"])
            if num(v) is not None}


def ano_da_tabela(df: pd.DataFrame) -> str | None:
    c = next((x for x in df.columns if x.strip() == "Ano"), None)
    return str(df[c].iloc[0]) if c is not None and len(df) else None


for m in MUNICIPIOS:
    cod = m.codigo_ibge
    scod = str(cod)
    populacao = sidra_val(pop, cod, "População residente")
    pib_total, ano_pib = sidra_ultimo(pib, cod, "Produto Interno Bruto a preços")
    va = {k: sidra_ultimo(pib, cod, t) for k, t in (
        ("total", "Valor adicionado bruto a preços correntes total"),
        ("agro", "da agropecuária"), ("ind", "da indústria"),
        ("serv", "dos serviços"), ("adm", "da administração"),
        ("imp", "Impostos, líquidos"))}
    cem_ul, ano_cem = sidra_ultimo(cem, cod, "unidades locais")

    # --- demografia ---------------------------------------------------------
    piramide = []
    if not pir.empty:
        cm = next(c for c in pir.columns if c.startswith("Município (Código)"))
        cs = next((c for c in pir.columns if c.strip() == "Sexo"), None)
        ci = next((c for c in pir.columns if c.strip() == "Idade"), None)
        sub = pir[pir[cm] == scod]
        for _, r in sub.iterrows():
            piramide.append({"sexo": r.get(cs), "faixa": r.get(ci),
                             "pessoas": num(r.get("Valor"))})

    # A 9923 traz a situacao do domicilio como CLASSIFICACAO, nao como
    # variavel - o rotulo "Urbana"/"Rural" esta na coluna propria.
    urb = rur = None
    if not sit.empty:
        cm = next(c for c in sit.columns if c.startswith("Município (Código)"))
        cc = next((c for c in sit.columns
                   if "situação do domicílio" in c.strip().lower()
                   and "código" not in c.lower()), None)
        sub = sit[sit[cm] == scod]
        for _, r in sub.iterrows():
            rot = str(r.get(cc, "")).strip().lower()
            if rot == "urbana":
                urb = num(r.get("Valor"))
            elif rot == "rural":
                rur = num(r.get("Valor"))

    # --- trabalho no turismo ------------------------------------------------
    tur = {}
    if not rais_mun.empty:
        s = rais_mun[rais_mun.codigo_ibge.astype(str) == scod]
        if len(s):
            tur = {"vinculos": int(float(s.vinculos.iloc[0])),
                   "remuneracao_media": num(s.remuneracao_media.iloc[0]),
                   "remuneracao_mediana": num(s.remuneracao_mediana.iloc[0])}
    por_act = {}
    if not rais_act.empty:
        s = rais_act[rais_act.codigo_ibge.astype(str) == scod]
        por_act = {r.ACT: int(float(r.vinculos)) for r in s.itertuples()}
    por_sexo = {}
    if not rais_sexo.empty:
        s = rais_sexo[rais_sexo.codigo_ibge.astype(str) == scod]
        por_sexo = {r.Sexo: int(float(r.vinculos)) for r in s.itertuples()}

    # --- campo --------------------------------------------------------------
    campo = {}
    if not vinculo.empty:
        v = vinculo[vinculo.cod_municipio_ponto.astype(str).str.startswith(scod)
                    if "cod_municipio_ponto" in vinculo.columns
                    else vinculo.cod_municipio.astype(str) == scod]
        campo["fichas_vinculadas"] = int(v.vinculado.sum()) if len(v) else 0
        campo["por_formulario"] = (
            v[v.vinculado].formulário.value_counts().to_dict() if len(v) else {})
    if not cobertura.empty:
        c = cobertura[cobertura["Código IBGE"] == cod]
        if len(c):
            r = c.iloc[0]
            campo["pontos_selecionados"] = int(r["Pontos de aferição selecionados"])
            campo["fotografias"] = int(r["Fotografias"])
            campo["videos"] = int(r["Vídeos"])
            campo["entrevista_secretaria"] = bool(r["Entrevista secretaria"])
            campo["checklists_nauticos"] = int(r["Checklist náutico"])

    # --- lacunas ------------------------------------------------------------
    lacunas = []
    if m.uf != "PR":
        lacunas.append("Série histórica do IPARDES não se aplica: a base cobre "
                       "apenas o Paraná.")
    if m.uf == "MS":
        lacunas.append("Perfil da SEMADESC disponível, mas com a maioria dos "
                       "indicadores ancorada no Censo 2010.")
    if m.uf == "SC":
        lacunas.append("Não coberto por base estadual (nem IPARDES, nem "
                       "SEMADESC); depende integralmente de fonte nacional.")
    if campo.get("checklists_nauticos", 0) == 0 and m.agua_navegavel:
        lacunas.append("Tem corpo d'água navegável, mas não há checklist de "
                       "infraestrutura náutica.")
    if not campo.get("entrevista_secretaria", True):
        lacunas.append("Sem entrevista com a secretaria municipal de turismo.")
    # pontos que constavam do plano de campo e nao chegaram a ser aferidos
    previstos = SEM_COLETA.get(m.slug, {}).get("pontos", [])
    if previstos:
        nomes = "; ".join(
            p["nome"] + (f" ({p['local']})" if p.get("local") else "")
            for p in previstos)
        lacunas.append(
            ("Ponto previsto no plano de campo e não aferido: "
             if len(previstos) == 1 else
             "Pontos previstos no plano de campo e não aferidos: ") + nomes + ".")

    perfil = {
        "identificacao": {
            "codigo_ibge": cod, "nome": m.nome, "uf": m.uf,
            "ordem_no_caderno": m.ordem,
            "regiao_imediata": m.reg_imediata,
            "regiao_intermediaria": m.reg_intermediaria,
            "perfil_na_rede": m.perfil,
            "linha_internacional": m.linha_internacional,
            "pais_vizinho": m.pais_vizinho or None,
            "tem_aerodromo": m.tem_aerodromo,
            "agua_navegavel": m.agua_navegavel,
        },
        "turismo_institucional": {
            "regiao_turistica": mtur_campo(mapa, cod, "REGIAO_TURISTICA",
                                           "REGIÃO_TURISTICA"),
            "categoria_mtur": mtur_campo(categ, cod, "CATEGORIA", "CLUSTER"),
            "fonte": "Mapa do Turismo Brasileiro e Categorização (MTur, 2019)",
        },
        "demografia": {
            "populacao_censo2022": populacao,
            "area_km2": sidra_val(area, cod, "Área"),
            "densidade_hab_km2": sidra_val(area, cod, "Densidade"),
            "taxa_crescimento_geometrico": sidra_val(pop, cod, "crescimento"),
            "populacao_urbana": urb, "populacao_rural": rur,
            "grau_urbanizacao_pct": (round(urb / (urb + rur) * 100, 1)
                                     if urb and rur else None),
            "domicilios_ocupados": sidra_val(
                dom, cod, "Domicílios particulares permanentes ocupados"),
            "moradores_por_domicilio": sidra_val(dom, cod, "Média de moradores"),
            "piramide_etaria": piramide,
            "fonte": "IBGE — Censo Demográfico 2022 (tabelas 4709, 4714, 9923, "
                     "4712 e 9514), via SIDRA",
        },
        "economia": {
            "ano_referencia": ano_pib,
            "pib_mil_reais": pib_total,
            "pib_serie": sidra_serie(pib, cod, "Produto Interno Bruto a preços"),
            # A tabela 5938 nao publica PIB per capita; e calculado aqui, com a
            # populacao do Censo 2022. O PIB e de outro ano de referencia
            # (ano_referencia), entao a razao mistura anos.
            "pib_per_capita_calculado": (round(pib_total * 1000 / populacao, 2)
                                         if pib_total and populacao else None),
            # o VA setorial sai um ano depois do PIB total: ano proprio
            "ano_va": va["total"][1],
            "va_total": va["total"][0],
            "va_agropecuaria": va["agro"][0],
            "va_industria": va["ind"][0],
            "va_servicos": va["serv"][0],
            "va_administracao": va["adm"][0],
            "impostos": va["imp"][0],
            "ano_cempre": ano_cem,
            "pessoal_ocupado_cempre": sidra_ultimo(cem, cod, "Pessoal ocupado total")[0],
            "salario_medio_cempre_sm": sidra_ultimo(cem, cod, "Salário médio mensal")[0],
            "unidades_locais_cempre": cem_ul,
            "fonte": "IBGE — PIB dos Municípios (5938) e CEMPRE (1685), via SIDRA",
        },
        "trabalho_no_turismo": {
            "total": tur, "por_act": por_act, "por_sexo": por_sexo,
            "fonte": "RAIS 2025, via Dados Abertos do Ministério do Turismo",
        },
        "oferta_cadastur": {
            cat: int(cont.get(scod, 0)) for cat, cont in cadastur.items()
        },
        "pesquisa_de_campo": campo,
        "lacunas_de_informacao": lacunas,
    }

    m.dir_dados.mkdir(parents=True, exist_ok=True)
    (m.dir_dados / "perfil_municipal.json").write_text(
        json.dumps(perfil, ensure_ascii=False, indent=2), encoding="utf-8")
    perfis.append(perfil)

    d = perfil["demografia"]
    e = perfil["economia"]
    linhas_comparativo.append({
        "Ordem": m.ordem, "Município": m.nome, "UF": m.uf,
        "Região turística": perfil["turismo_institucional"]["regiao_turistica"],
        "Categoria MTur": perfil["turismo_institucional"]["categoria_mtur"],
        "População 2022": d["populacao_censo2022"],
        "Área (km²)": d["area_km2"],
        "Densidade": d["densidade_hab_km2"],
        "% urbana": d["grau_urbanizacao_pct"],
        "PIB (mil R$)": e["pib_mil_reais"],
        "PIB per capita": e["pib_per_capita_calculado"],
        "Vínculos turismo": tur.get("vinculos"),
        "Remuneração média turismo": tur.get("remuneracao_media"),
        "CADASTUR (total)": sum(perfil["oferta_cadastur"].values()),
        "Pontos de aferição": campo.get("pontos_selecionados"),
        "Fichas vinculadas": campo.get("fichas_vinculadas"),
        "Fotografias": campo.get("fotografias"),
        "Lacunas": len(lacunas),
    })

C = pd.DataFrame(linhas_comparativo).sort_values("Ordem")
with pd.ExcelWriter(DIR_DADOS / "perfis_municipais.xlsx",
                    engine="openpyxl") as w:
    C.to_excel(w, sheet_name="Comparativo", index=False)

print("=" * 100)
print("PERFIS MUNICIPAIS CONSOLIDADOS")
print("=" * 100)
with pd.option_context("display.width", 260, "display.max_columns", 30):
    print(C.drop(columns=["Ordem", "Região turística"]).to_string(index=False))

vazios = [(r["Município"], c) for _, r in C.iterrows()
          for c in ("População 2022", "PIB (mil R$)", "Vínculos turismo")
          if pd.isna(r[c])]
print(f"\nCampos essenciais sem valor: {len(vazios)}")
for mu, c in vazios:
    print(f"   {mu}: {c}")

print(f"\n{len(perfis)} perfis gravados em 02_Dados_Municipais/<município>/")
print(f"Comparativo: {DIR_DADOS / 'perfis_municipais.xlsx'}")
