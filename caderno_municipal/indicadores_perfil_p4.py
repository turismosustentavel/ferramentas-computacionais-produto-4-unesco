# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
INDICADORES DO PERFIL MUNICIPAL E POSICAO ENTRE OS DOZE MUNICIPIOS
================================================================================
A partir do perfil consolidado de cada municipio (12_montar_perfil_municipal.py)
calcula tres conjuntos de indicadores:

    estrutura etaria   Censo 2022: participacao das faixas de ate 14 anos, de
                       15 a 64 e de 65 ou mais, participacao das mulheres,
                       razao de dependencia e faixa mais numerosa; idades de
                       90 anos ou mais agrupadas numa faixa
    valor adicionado   composicao por setor (industria, servicos,
                       administracao publica, agropecuaria) no ultimo ano com
                       os setores publicados no SIDRA
    posicao            sete indicadores comparados entre os doze municipios do
                       estudo (lista em INDICADORES)

METODO
    Posicao
        Entram so os municipios com valor no indicador. A posicao e 1 mais o
        numero de municipios com valor estritamente maior: o maior valor e o
        1o, e valores empatados recebem a mesma posicao, a melhor (dois
        municipios empatados no maior valor ficam ambos em 1o; o seguinte,
        em 3o). "de" e o numero de municipios com valor.
    Vinculos no turismo por 100 hab.
        vinculos formais nas ACTs (RAIS) / populacao do Censo 2022 x 100;
        vazio se faltar um dos dois.
    Estrutura etaria
        percentuais sobre o total de pessoas da piramide do Censo 2022;
        15 a 64 = 100 - (ate 14) - (65 ou mais);
        razao de dependencia = (ate 14 + 65 ou mais) / (15 a 64) x 100;
        faixa mais numerosa: em empate, a mais jovem.
    Valor adicionado
        entram os setores com valor publicado (nao nulo); a participacao de
        cada setor e calculada sobre a soma desses setores, e nao sobre o VA
        total, que inclui impostos. Calculado so quando o VA total existe.

ENTRADAS (caminhos relativos a P4_DADOS; ver comum.py)
    Entregas/Produto 4/produção/Caderno de informações por município/
        02_Dados_Municipais/<slug>/perfil_municipal.json
        gerado por 12_montar_perfil_municipal.py (IBGE/SIDRA: Censo 2022,
        PIB dos Municipios; RAIS; CADASTUR)

SAIDAS (em Entregas/Produto 4/produção/Caderno de informações por município/
        02_Dados_Municipais/)
    indicadores_perfil.csv e indicadores_perfil.xlsx
        um registro por municipio e indicador: valor, unidade, posicao e
        numero de municipios com valor
    <slug>/metricas_perfil_<slug>.json
        estrutura etaria, valor adicionado e posicao do municipio em cada
        indicador

COMO EXECUTAR
    python indicadores_perfil_p4.py

    Uso como modulo:
        import indicadores_perfil_p4 as ip
        todos = ip.todos_indicadores()
        ip.posicoes(todos)["Medianeira"]
================================================================================
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from comum import DIR_DADOS, MUNICIPIOS, POR_SLUG                # noqa: E402

ARQ_TABELA = DIR_DADOS / "indicadores_perfil"

# Indicadores comparados entre os doze, na ordem de leitura, com a unidade
INDICADORES = {
    "População (2022)": "habitantes",
    "Grau de urbanização": "% da população",
    "PIB per capita": "R$ por habitante",
    "Vínculos formais no turismo": "vínculos",
    "Vínculos no turismo por 100 hab.": "vínculos por 100 habitantes",
    "Meios de hospedagem (CADASTUR)": "cadastros",
    "Agências de turismo (CADASTUR)": "cadastros",
}


# ══════════════════════════════════════════════════════════════════════════════
# LEITURA
# ══════════════════════════════════════════════════════════════════════════════
def perfil(slug: str) -> dict:
    """Perfil consolidado do município (12_montar_perfil_municipal.py)."""
    return json.loads((DIR_DADOS / slug / "perfil_municipal.json")
                      .read_text("utf-8"))


# ══════════════════════════════════════════════════════════════════════════════
# ESTRUTURA ETARIA
# ══════════════════════════════════════════════════════════════════════════════
def faixas_etarias(p: dict) -> dict[int, dict]:
    """Pessoas por faixa etária e sexo; chave = idade inicial da faixa.

    As faixas de 90 anos ou mais são somadas numa só, de chave 90.
    """
    pir = p["demografia"].get("piramide_etaria") or []
    faixas: dict[int, dict] = {}
    for x in pir:
        ini = int(re.match(r"(\d+)", x["faixa"]).group(1))
        rot = "90 ou mais" if ini >= 90 else x["faixa"].replace(" anos", "")
        k = min(ini, 90)
        faixas.setdefault(k, {"rot": rot, "Homens": 0.0, "Mulheres": 0.0})
        faixas[k][x["sexo"]] += x["pessoas"] or 0
    return faixas


def piramide_percentual(p: dict) -> list[dict]:
    """Participação de cada faixa e sexo na população total, em %."""
    faixas = faixas_etarias(p)
    if not faixas:
        return []
    ordem = sorted(faixas)
    total = sum(f["Homens"] + f["Mulheres"] for f in faixas.values())
    return [{"faixa": faixas[k]["rot"],
             "homens_pct": faixas[k]["Homens"] / total * 100,
             "mulheres_pct": faixas[k]["Mulheres"] / total * 100}
            for k in ordem]


def estrutura_etaria(p: dict) -> dict | None:
    """Grandes grupos de idade, mulheres e razão de dependência, em %."""
    faixas = faixas_etarias(p)
    if not faixas:
        return None
    ordem = sorted(faixas)
    total = sum(f["Homens"] + f["Mulheres"] for f in faixas.values())
    jovens = sum((faixas[k]["Homens"] + faixas[k]["Mulheres"])
                 for k in ordem if k < 15) / total * 100
    idosos = sum((faixas[k]["Homens"] + faixas[k]["Mulheres"])
                 for k in ordem if k >= 65) / total * 100
    ativos = 100 - jovens - idosos
    mulheres = sum(f["Mulheres"] for f in faixas.values()) / total * 100
    maior = max(ordem,
                key=lambda k: faixas[k]["Homens"] + faixas[k]["Mulheres"])
    return {
        "ate_14_pct": round(jovens, 1), "de_15_a_64_pct": round(ativos, 1),
        "65_ou_mais_pct": round(idosos, 1), "mulheres_pct": round(mulheres, 1),
        "razao_dependencia": round((jovens + idosos) / ativos * 100, 1),
        "faixa_mais_numerosa": faixas[maior]["rot"],
    }


# ══════════════════════════════════════════════════════════════════════════════
# VALOR ADICIONADO
# ══════════════════════════════════════════════════════════════════════════════
def valor_adicionado(p: dict) -> dict | None:
    """Composição setorial do valor adicionado, do maior setor ao menor."""
    e = p["economia"]
    setores = [("Indústria", e.get("va_industria")),
               ("Serviços", e.get("va_servicos")),
               ("Administração pública", e.get("va_administracao")),
               ("Agropecuária", e.get("va_agropecuaria"))]
    setores = [(n, v) for n, v in setores if v]
    if not (setores and e.get("va_total")):
        return None
    tot = sum(v for _, v in setores)
    setores.sort(key=lambda s: -s[1])
    return {
        "ano": e.get("ano_va"),
        "total_mil_reais": tot,
        "setores": [{"setor": n, "mil_reais": v,
                     "pct": round(v / tot * 100, 1)} for n, v in setores],
    }


# ══════════════════════════════════════════════════════════════════════════════
# POSICAO ENTRE OS DOZE
# ══════════════════════════════════════════════════════════════════════════════
def indicadores(p: dict) -> dict:
    """Valor de cada indicador de INDICADORES (None quando não há dado)."""
    d, e = p["demografia"], p["economia"]
    t = p.get("trabalho_no_turismo", {}).get("total") or {}
    cad = p.get("oferta_cadastur", {})
    pop = d.get("populacao_censo2022")
    vinc = t.get("vinculos")
    return {
        "População (2022)": pop,
        "Grau de urbanização": d.get("grau_urbanizacao_pct"),
        "PIB per capita": e.get("pib_per_capita_calculado"),
        "Vínculos formais no turismo": vinc,
        "Vínculos no turismo por 100 hab.": (vinc / pop * 100
                                             if vinc and pop else None),
        "Meios de hospedagem (CADASTUR)": cad.get("meios_de_hospedagem"),
        "Agências de turismo (CADASTUR)": cad.get("agencias"),
    }


def todos_indicadores() -> dict[str, dict]:
    """{nome do município: indicadores} para os doze, na ordem do registro."""
    return {m.nome: indicadores(perfil(m.slug)) for m in MUNICIPIOS}


def posicoes(todos: dict[str, dict]) -> dict[str, dict[str, dict]]:
    """Posição de cada município em cada indicador.

    Devolve {município: {indicador: {"posicao", "de", "valor"}}}. O
    município sem valor num indicador não tem entrada para ele. Empate
    recebe a mesma posição, a melhor.
    """
    nomes_ind = list(next(iter(todos.values())).keys())
    saida: dict[str, dict[str, dict]] = {n: {} for n in todos}
    for ind in nomes_ind:
        vals = [(n, todos[n][ind]) for n in todos
                if todos[n][ind] is not None]
        vals.sort(key=lambda x: -x[1])
        n_val = len(vals)

        def _pos(v):
            return 1 + sum(1 for _, w in vals if w > v)

        for n, v in vals:
            saida[n][ind] = {"posicao": _pos(v), "de": n_val, "valor": v}
    return saida


def metricas_perfil(slug: str, todos: dict[str, dict] | None = None) -> dict:
    """Estrutura etária, valor adicionado e posição de um município."""
    m = POR_SLUG[slug]
    p = perfil(slug)
    if todos is None:
        todos = todos_indicadores()
    met: dict = {"municipio": m.nome_uf}
    pir = estrutura_etaria(p)
    if pir is not None:
        met["piramide"] = pir
    va = valor_adicionado(p)
    if va is not None:
        met["valor_adicionado"] = va
    met["posicao_regional"] = posicoes(todos)[m.nome]
    return met


def tabela(todos: dict[str, dict]) -> pd.DataFrame:
    """Um registro por município e indicador, com valor e posição."""
    pos = posicoes(todos)
    com_valor = {ind: sum(1 for n in todos if todos[n][ind] is not None)
                 for ind in INDICADORES}
    linhas = []
    for m in MUNICIPIOS:
        for ind, unidade in INDICADORES.items():
            r = pos[m.nome].get(ind)
            linhas.append({
                "ordem": m.ordem, "codigo_ibge": m.codigo_ibge,
                "municipio": m.nome, "uf": m.uf,
                "indicador": ind, "unidade": unidade,
                "valor": todos[m.nome][ind],
                "posicao": r["posicao"] if r else None,
                "de": com_valor[ind],
            })
    t = pd.DataFrame(linhas)
    t["posicao"] = t["posicao"].astype("Int64")
    return t


# ══════════════════════════════════════════════════════════════════════════════
# EXECUCAO
# ══════════════════════════════════════════════════════════════════════════════
def main() -> None:
    todos = todos_indicadores()
    if list(next(iter(todos.values()))) != list(INDICADORES):
        raise RuntimeError("INDICADORES e indicadores() divergem")
    t = tabela(todos)
    t.to_csv(ARQ_TABELA.with_suffix(".csv"), index=False,
             encoding="utf-8-sig")
    with pd.ExcelWriter(ARQ_TABELA.with_suffix(".xlsx"),
                        engine="openpyxl") as w:
        t.to_excel(w, sheet_name="Indicadores", index=False)
    print(f"-> {ARQ_TABELA.with_suffix('.csv')}")
    print(f"-> {ARQ_TABELA.with_suffix('.xlsx')}")

    for m in MUNICIPIOS:
        met = metricas_perfil(m.slug, todos)
        arq = DIR_DADOS / m.slug / f"metricas_perfil_{m.slug}.json"
        arq.write_text(json.dumps(met, ensure_ascii=False, indent=1),
                       "utf-8")
        print(f"-> {arq}")

    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print("\nPOSICAO ENTRE OS DOZE (1 = maior valor)")
        print(t.pivot(index="municipio", columns="indicador",
                      values="posicao")
              .reindex(index=[m.nome for m in MUNICIPIOS],
                       columns=list(INDICADORES)).to_string())


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
