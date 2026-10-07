# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMAÇÕES POR MUNICÍPIO | PRODUTO 4
AVALIAÇÃO DOS PONTOS AFERIDOS: FICHAS POR PONTO E MÉDIAS POR DIMENSÃO
================================================================================
Reúne as fichas de campo (Jotform: Geral, Rodoviária, Aeroporto, Aduana) por
ponto aferido e calcula as médias de avaliação, na escala de 1 a 5 (maior =
melhor), por ponto, por dimensão transversal e por bloco do formulário.

PRODUTOS
    fichas_<slug>.json
        índice por ponto ("Ponto #n"): formulário, linha da ficha no CSV do
        Jotform (convenção do vínculo: índice + 2), ponto vinculado, número
        de avaliações e de itens de presença, itens de presença
        ([item, existe]) e caracterização da via (só formulário Geral:
        cobertura, manutenção, faixas, sinalização de trânsito, fluxo e
        tipos de fluxo)
    metricas_matrizes_<slug>.json
        grade        uma linha por ponto: número, nome abreviado (42
                     caracteres) e nome completo (200 caracteres) por
                     comum.rotulo_curto, grupo, formulário, número de
                     avaliações, média por dimensão e por bloco (duas casas)
        chegada, interna
                     por grupo (null quando o grupo não tem ponto): número
                     de pontos, colunas comparadas e tipo de coluna; média
                     por coluna (duas casas, em ordem crescente); os quatro
                     menores registros (ponto, coluna, nota com uma casa);
                     registros abaixo de LIMIAR_REGULAR; total de registros

MÉTODO
    Vínculo ficha-ponto: aba "Vínculo" de vinculo_fichas_pontos.xlsx, só os
        registros vinculados cujo município do ponto começa pelo nome do
        município; ordem pelo número do ponto.
    Notas: fichas_p4.notas, com as escalas normalizadas para maior = melhor
        (inclusive as invertidas); escalas de intensidade (fluxo,
        movimentação) descrevem volume, não qualidade, e ficam fora.
    Dimensão transversal: cada item avaliado vai para a primeira dimensão de
        DIMENSOES cujo termo aparece no nome do item (sem acento, em
        minúsculas). Item sem dimensão não entra nas médias por dimensão,
        mas entra nas médias por bloco. Ponto sem nenhum item numa dimensão
        fica fora da grade.
    Médias: média aritmética das notas do ponto em cada dimensão e em cada
        bloco.
    Grupo: "chegada" quando a categoria do ponto na camada consolidada
        contém um dos termos de CHEGADA; "interna" nos demais.
    Colunas do grupo: quando todos os pontos do grupo usam o mesmo
        formulário, os blocos desse formulário (na ordem do formulário),
        porque respondem às mesmas perguntas; com formulários distintos, as
        dimensões transversais (na ordem de DIMENSOES). Média por coluna =
        média das médias dos pontos; menores registros = as quatro menores
        médias ponto × coluna.

ENTRADAS (relativas a P4_DADOS)
    Entregas/Produto 4/produção/Caderno de informações por município/
        02_Dados_Municipais/vinculo_fichas_pontos.xlsx
            vínculo de cada ficha ao ponto (04_vinculo_fichas_pontos.py)
    Levantamentos e Análises/Produto 4/03_Pesquisa_de_Campo_Primaria/
        01_Jotform_Bruto/Formulário_*.csv
            exportação das fichas, lida por fichas_p4 (contém dados pessoais
            da equipe de campo e não é distribuída)
        03_Pontos_Afericao/vetores_gis/pontos_afericao_consolidados.geojson
            categoria e nome de cada ponto (campos ordem, categoria, rotulo,
            nome_ponto)
    Módulos: fichas_p4 (leitura das fichas, notas, presenças, via, blocos),
    comum (rotulo_curto).

SAÍDAS
    Entregas/Produto 4/produção/Caderno de informações por município/
        02_Dados_Municipais/<slug>/fichas_<slug>.json
        02_Dados_Municipais/<slug>/metricas_matrizes_<slug>.json

COMO EXECUTAR
    python avaliacao_pontos_p4.py 01_Foz_do_Iguacu_PR
    python avaliacao_pontos_p4.py 02_Medianeira_PR 06_Guaira_PR

    O argumento é o slug de comum.MUNICIPIOS (um ou mais). As médias são
    calculadas a partir do índice de fichas gravado na mesma execução.

ORDEM
    Depende de 04_vinculo_fichas_pontos.py e da camada consolidada de pontos
    já corrigida e nomeada (18_corrigir_camada_pontos.py,
    31_nomes_oficiais_pontos.py). As saídas são lidas por
    indicadores_campo_p4 (presenças, via e médias) e por
    indicadores_municipais_p4 (postos de fronteira aferidos).
================================================================================
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import fichas_p4 as fp                                           # noqa: E402
from comum import (CAMPO, DIR_DADOS, MUNICIPIOS, POR_SLUG,       # noqa: E402
                   rotulo_curto)

VINCULO = DIR_DADOS / "vinculo_fichas_pontos.xlsx"
PONTOS = (CAMPO / "03_Pontos_Afericao" / "vetores_gis" /
          "pontos_afericao_consolidados.geojson")

# ══════════════════════════════════════════════════════════════════════════════
# PARÂMETROS
# ══════════════════════════════════════════════════════════════════════════════
# Termos da categoria do ponto que o põem no grupo de chegada.
CHEGADA = ("Rodovia", "Terminal", "Aeroporto", "Aduana")

# Dimensões transversais, na ordem de leitura: (nome, termos no nome do item,
# sem acento e em minúsculas). A primeira que casar vence.
DIMENSOES = [
    ("Conservação", ("manutenc", "conservac", "estado de", "pavimento")),
    ("Limpeza", ("lixo", "limpeza")),
    ("Vegetação", ("vegetac", "arboriz", "sombreamento")),
    ("Iluminação", ("iluminac",)),
    ("Conforto", ("conforto", "termic", "sonor", "assento", "cobertura",
                  "abrigo", "sombra", "ruido")),
    ("Segurança", ("seguranc", "polic", "monitor", "vigilan", "permeabilidade")),
    ("Acessibilidade", ("acessibilidade", "piso tatil", "rampa", "rebaixamento",
                        "cadeirante", "mobilidade reduzida")),
    ("Sinalização", ("sinalizac", "placa", "faixa de pedestre")),
    ("Informação", ("informac", "painel", "atendimento", "orientac")),
    ("Filas", ("fila", "organizac", "controle de acesso", "espera")),
]

# Tamanho do nome do ponto: abreviado e completo (comum.rotulo_curto).
NOME_CURTO, NOME_COMPLETO = 42, 200
# Abaixo desta média o registro fica abaixo de "regular" (3).
LIMIAR_REGULAR = 2.5
MENORES = 4                       # menores registros guardados por grupo


# ══════════════════════════════════════════════════════════════════════════════
# FICHAS POR PONTO
# ══════════════════════════════════════════════════════════════════════════════
def vinculos(m) -> pd.DataFrame:
    """Fichas vinculadas a pontos do município, pela ordem do ponto."""
    vinc = pd.read_excel(VINCULO, sheet_name="Vínculo")
    vm = vinc[(vinc.municipio_do_ponto.astype(str).str.startswith(m.nome))
              & vinc.vinculado].copy()
    vm["numero"] = vm.ordem.astype(str).str.extract(r"(\d+)").astype(int)
    return vm.sort_values("numero")


def fichas_por_ponto(m) -> dict:
    """{"Ponto #n": {formulario, linha_csv, ponto, n_avaliacoes,
    n_presencas, presencas, via}}."""
    indice = {}
    for v in vinculos(m).itertuples():
        # itertuples renomeia para _<posição> a coluna de nome inválido
        form = v._1 if hasattr(v, "_1") else v.formulário
        reg = fp.registro(form, v.linha_csv)
        notas = fp.notas(form, reg)
        pres = fp.presencas(form, reg)
        indice[v.ordem] = {
            "formulario": form, "linha_csv": int(v.linha_csv),
            "ponto": v.ponto_vinculado,
            "n_avaliacoes": len(notas), "n_presencas": len(pres),
            # a lista, e não só a contagem: o que existe e o que falta em
            # cada ponto
            "presencas": [[nome, bool(tem)] for nome, tem in pres],
            "via": fp.via(form, reg),
        }
        print(f"{v.ordem:<10} {form:<11} {len(notas):>2} avaliações · "
              f"{len(pres):>2} presenças")
    return indice


# ══════════════════════════════════════════════════════════════════════════════
# MÉDIAS POR DIMENSÃO E POR BLOCO
# ══════════════════════════════════════════════════════════════════════════════
def chave(s: str) -> str:
    t = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def dimensao_de(item: str):
    """A dimensão transversal do item avaliado, ou None."""
    k = chave(item)
    for nome, termos in DIMENSOES:
        if any(t in k for t in termos):
            return nome
    return None


def categorias_e_nomes(m) -> tuple[dict, dict]:
    """({ordem: categoria}, {ordem: nome}) da camada consolidada. O nome é
    o `rotulo` (com o qualificador da área de análise onde o nome se repete
    no município), ou `nome_ponto` sem ele."""
    cons = gpd.read_file(PONTOS)
    pontos = cons[cons.cidade == m.nome].copy()
    categoria = dict(zip(pontos.ordem.astype(str),
                         pontos.categoria.astype(str)))
    col_nome = "rotulo" if "rotulo" in pontos.columns else "nome_ponto"
    nome = dict(zip(pontos.ordem.astype(str),
                    pontos[col_nome].fillna(pontos.nome_ponto).astype(str)))
    return categoria, nome


def linhas_de_avaliacao(m, fichas: dict) -> list[dict]:
    """Uma linha por ponto com ao menos um item numa dimensão."""
    categoria, nome_ponto = categorias_e_nomes(m)
    linhas = []
    for ordem, f in fichas.items():
        reg = fp.registro(f["formulario"], f["linha_csv"])
        notas = fp.notas(f["formulario"], reg)
        por_dim: dict[str, list[int]] = {}
        for n in notas:
            d = dimensao_de(n["item"])
            if d:
                por_dim.setdefault(d, []).append(n["nota"])
        if not por_dim:
            continue
        por_bloco: dict[str, list[int]] = {}
        for n in notas:
            por_bloco.setdefault(n["bloco"], []).append(n["nota"])
        cat = categoria.get(ordem, "")
        nome = nome_ponto.get(ordem, f["ponto"])
        linhas.append({
            "ordem": ordem,
            "numero": int(re.search(r"(\d+)", ordem).group(1)),
            "nome": rotulo_curto(nome, m.nome, NOME_CURTO),
            "nome_texto": rotulo_curto(nome, m.nome, NOME_COMPLETO),
            "formulario": f["formulario"],
            "grupo": "chegada" if any(c in cat for c in CHEGADA) else "interna",
            "dimensao": {d: float(np.mean(v)) for d, v in por_dim.items()},
            "bloco": {b: float(np.mean(v)) for b, v in por_bloco.items()},
            "n_avaliacoes": len(notas),
        })
    linhas.sort(key=lambda r: r["numero"])
    return linhas


def colunas_do_grupo(dados: list[dict]) -> tuple[str, list[str]]:
    """(tipo de coluna, colunas): blocos do formulário, quando o grupo usa
    um só; dimensões transversais, quando usa mais de um."""
    forms = {r["formulario"] for r in dados}
    if len(forms) == 1:
        form = forms.pop()
        campo = "bloco"
        ordem_cols = [t for t, _ in fp.BLOCOS[form]]
        cols = [c for c in ordem_cols if any(c in r["bloco"] for r in dados)]
    else:
        campo = "dimensao"
        cols = [d for d, _ in DIMENSOES
                if any(d in r["dimensao"] for r in dados)]
    return campo, cols


def resumo_do_grupo(linhas: list[dict], grupo: str) -> dict | None:
    """Colunas, médias por coluna e menores registros do grupo."""
    dados = [r for r in linhas if r["grupo"] == grupo]
    if not dados:
        return None
    campo, cols = colunas_do_grupo(dados)
    saida = {"pontos": len(dados), "colunas": cols, "tipo_de_coluna": campo}
    todas = [(r["nome_texto"], d, v) for r in dados for d, v in r[campo].items()]
    piores = sorted(todas, key=lambda t: t[2])[:MENORES]
    por_col: dict[str, list[float]] = {}
    for _, d, v in todas:
        por_col.setdefault(d, []).append(v)
    med = {d: round(float(np.mean(v)), 2) for d, v in por_col.items()}
    saida.update({
        "media_por_coluna": dict(sorted(med.items(), key=lambda kv: kv[1])),
        "piores": [{"ponto": p, "coluna": d, "nota": round(v, 1)}
                   for p, d, v in piores],
        "abaixo_de_regular": sum(1 for _, _, v in todas if v < LIMIAR_REGULAR),
        "total_celulas": len(todas),
    })
    return saida


def metricas_matrizes(m, fichas: dict) -> dict:
    """Médias por grupo ("chegada", "interna") e a grade completa."""
    linhas = linhas_de_avaliacao(m, fichas)
    met = {"chegada": resumo_do_grupo(linhas, "chegada"),
           "interna": resumo_do_grupo(linhas, "interna")}
    met["grade"] = [{"numero": r["numero"], "nome": r["nome"],
                     "nome_texto": r["nome_texto"],
                     "grupo": r["grupo"], "formulario": r["formulario"],
                     "n_avaliacoes": r["n_avaliacoes"],
                     "dimensao": {k: round(v, 2)
                                  for k, v in r["dimensao"].items()},
                     "bloco": {k: round(v, 2) for k, v in r["bloco"].items()}}
                    for r in linhas]
    return met


# ══════════════════════════════════════════════════════════════════════════════
# EXECUÇÃO
# ══════════════════════════════════════════════════════════════════════════════
def arquivos(m) -> tuple[Path, Path]:
    pasta = DIR_DADOS / m.slug
    return (pasta / f"fichas_{m.slug}.json",
            pasta / f"metricas_matrizes_{m.slug}.json")


def gravar(m) -> list[Path]:
    """Grava o índice de fichas e, a partir dele, as médias."""
    arq_fichas, arq_med = arquivos(m)
    arq_fichas.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(fichas_por_ponto(m), ensure_ascii=False, indent=1)
    arq_fichas.write_text(texto, "utf-8")
    met = metricas_matrizes(m, json.loads(texto))
    arq_med.write_text(json.dumps(met, ensure_ascii=False, indent=1), "utf-8")
    return [arq_fichas, arq_med]


def main(argv: list[str] | None = None) -> None:
    args = [a for a in (sys.argv[1:] if argv is None else argv)
            if not a.startswith("--")]
    if not args:
        print("Informe o slug do município. Ex.: 01_Foz_do_Iguacu_PR")
        sys.exit(1)
    desconhecidos = [a for a in args if a not in POR_SLUG]
    if desconhecidos:
        print("Slug não reconhecido: " + ", ".join(desconhecidos))
        print("Válidos: " + ", ".join(m.slug for m in MUNICIPIOS))
        sys.exit(1)
    for slug in args:
        m = POR_SLUG[slug]
        print(f"\n{m.nome_uf}")
        for p in gravar(m):
            print("   " + str(p))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
