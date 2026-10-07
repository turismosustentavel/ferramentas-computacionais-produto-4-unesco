# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
LEITURA DAS FICHAS DE CAMPO
================================================================================
Le as quatro fichas aplicadas em campo (Jotform: Geral, Rodoviaria, Aeroporto,
Aduana) e classifica cada campo (nota em escala 1-5, sim/nao, valor), na
ordem do proprio formulario. Fornece as notas de avaliacao normalizadas, a
caracterizacao da via e os itens de presenca/ausencia de cada ponto.

ESCALAS
    O Jotform exporta as avaliacoes como numeros. Os rotulos vem dos modelos
    das fichas (04_Modelos_Fichas/modelos_pdf), que sao o instrumento aplicado.
    As escalas NAO sao uniformes, e duas armadilhas importam:

      - "Sensacao geral de seguranca" na ficha de rodoviaria e INVERTIDA:
        1 = muito seguro ... 5 = muito inseguro.
      - "Permeabilidade visual" na mesma ficha vai de 1 = muito alta/ruim a
        5 = muito baixa/visao limpa.

    Cada escala declara a sua direcao; `notas()` normaliza tudo para
    "maior = melhor". Valores fora da escala (a rodoviaria de
    Foz tem "Intensidade do fluxo = 100") sao reportados como tal, nunca
    reinterpretados.

    Verificacao: o relatorio do Produto 4 descreve a rodoviaria de Foz com
    conservacao "ruim" e limpeza "pessima"; a ficha traz 2 e 1. A leitura
    direta 1 = pessimo ... 5 = otimo e a adotada.

ENTRADA (relativa a P4_DADOS)
    Levantamentos e Análises/Produto 4/03_Pesquisa_de_Campo_Primaria/
        01_Jotform_Bruto/Formulário_*.csv  (exportacao do Jotform; contem
        dados pessoais da equipe de campo e nao e distribuida)
================================================================================
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from comum import JOTFORM

ARQUIVOS = {
    "Geral": "Formulário_Geral_-_Produto_04*.csv",
    "Rodoviária": "Formulário_Rodoviárias_-_Produt*.csv",
    "Aeroporto": "Formulário_Aeroportos_-_Produto*.csv",
    "Aduana": "Formulário_Aduanas_-_Produto_04*.csv",
}

# ── rotulos das escalas, dos modelos das fichas ──────────────────────────────
QUALIDADE = ["péssimo", "ruim", "regular", "bom", "ótimo"]
MOVIMENTO = ["muito pouco movimentado", "pouco movimentado", "regular",
             "movimentado", "muito movimentado"]
INTENSIDADE = ["muito baixo", "baixo", "regular", "alto", "muito alto"]
INTENSIDADE_F = ["muito baixa", "baixa", "moderada", "alta", "muito alta"]
MOVIMENTACAO = ["muito baixa", "baixa", "moderada", "alta", "muito alta/crítica"]
ORGANIZACAO = ["muito desorganizada", "desorganizada", "regular", "organizada",
               "muito organizada"]
EFICIENCIA = ["muito ineficiente", "ineficiente", "regular", "eficiente",
              "muito eficiente"]
ADEQUACAO = ["totalmente inadequada", "inadequada", "regular", "adequada",
             "totalmente adequada"]
FILA_ROD = ["inexistente", "pequena", "moderada", "grande", "excessiva/crítica"]
CONFORTO_ROD = ["muito insuficiente", "insuficiente", "regular", "adequado",
                "excelente"]
PERMEAB_ROD = ["muito alta/ruim", "alta", "moderada", "baixa",
               "muito baixa/visão limpa"]
SEGURANCA_ROD = ["muito seguro", "seguro", "moderada", "inseguro",
                 "muito inseguro"]

# (fragmento do nome do campo, rotulos, maior_e_melhor)
# A primeira regra que casar vence: as especificas vem antes das genericas.
CONTINUIDADE = ["totalmente descontínuo", "com muita descontinuidade",
                "regular", "com uma ou duas descontinuidades",
                "totalmente contínuo"]

ESCALAS = {
    # Na ficha geral a maioria das notas vem como "4 - bom", mas parte vem so
    # como numero ("3", "5.0"). Sem estas regras o numero era lido como texto
    # e a nota sumia da regua.
    "Geral": [
        ("Fluxo", MOVIMENTO, None),
        ("Continuidade", CONTINUIDADE, True),
        ("LIKERT", QUALIDADE, True),
    ],
    "Rodoviária": [
        ("Intensidade do fluxo", INTENSIDADE, None),
        ("Movimentação observada", MOVIMENTACAO, None),
        ("Extensão das filas", FILA_ROD, False),
        ("Organização das filas", ORGANIZACAO, True),
        ("Controle de acesso", EFICIENCIA, True),
        ("Iluminação adequada", EFICIENCIA, True),
        ("Permeabilidade visual", PERMEAB_ROD, True),
        ("Sensação geral de segurança", SEGURANCA_ROD, False),
        ("Conforto geral", CONFORTO_ROD, True),
        ("Conservação", QUALIDADE, True), ("Limpeza", QUALIDADE, True),
        ("Manejo de resíduos", QUALIDADE, True),
        ("Acesso para pedestres", QUALIDADE, True),
        ("Condição geral", QUALIDADE, True),
        ("Qualidade geral", QUALIDADE, True),
        ("Assentos", QUALIDADE, True), ("Ventilação", QUALIDADE, True),
    ],
    "Aeroporto": [
        ("Intensidade do fluxo", INTENSIDADE_F, None),
        ("Movimentação observada", MOVIMENTACAO, None),
        ("Organização das filas", ORGANIZACAO, True),
        ("Conservação", QUALIDADE, True), ("Limpeza", QUALIDADE, True),
        ("Conforto", QUALIDADE, True), ("Manejo de resíduos", QUALIDADE, True),
        ("Acesso para pedestres", QUALIDADE, True),
        ("Condição geral", QUALIDADE, True), ("Qualidade geral", QUALIDADE, True),
        ("Iluminação adequada", QUALIDADE, True),
        ("Sensação geral", QUALIDADE, True), ("Assentos", QUALIDADE, True),
        ("Espaço de recepção", QUALIDADE, True),
    ],
    "Aduana": [
        ("Intensidade do fluxo", INTENSIDADE, None),
        ("Organização das filas", ORGANIZACAO, True),
        ("Área segura", ADEQUACAO, True),
        ("conservação", QUALIDADE, True), ("Limpeza", QUALIDADE, True),
        ("Manejo de resíduos", QUALIDADE, True),
        ("Acesso para pedestres", QUALIDADE, True),
        ("Condição geral", QUALIDADE, True), ("Qualidade geral", QUALIDADE, True),
        ("Sensação geral", QUALIDADE, True), ("Conforto", QUALIDADE, True),
    ],
}

# ── blocos, pelos indices de coluna de cada formulario ───────────────────────
R = lambda a, b: list(range(a, b + 1))                         # noqa: E731
BLOCOS = {
    "Geral": [
        ("A via", R(4, 15)),
        ("Calçada, travessia e acessibilidade", R(16, 31)),
        ("Ciclovia", R(32, 41)),
        ("Faixas exclusivas", R(42, 69)),
        ("Transporte coletivo", R(70, 111)),
        ("Ponto de táxi", R(112, 121)),
        ("Observações da equipe", [122]),
    ],
    "Rodoviária": [
        ("Condições da visita", R(3, 4)),
        ("Fluxo e filas", R(5, 11)),
        ("Conservação e limpeza", R(12, 18)),
        ("Inserção urbana e acessos", R(19, 30)),
        ("Acessibilidade", R(31, 39)),
        ("Sinalização e informação", R(40, 48)),
        ("Segurança", R(49, 54)),
        ("Área de espera", R(55, 63)),
        ("Serviços", R(64, 74)),
        ("Conexões", R(75, 80)),
    ],
    "Aeroporto": [
        ("Condições da visita e operação", R(3, 11)),
        ("Fluxo e filas", R(12, 21)),
        ("Conservação, limpeza e conforto", R(22, 30)),
        ("Inserção urbana e acessos", R(31, 40)),
        ("Acessibilidade", R(41, 49)),
        ("Sinalização e informação", R(50, 58)),
        ("Segurança", R(59, 64)),
        ("Área de espera", R(65, 73)),
        ("Serviços", R(74, 84)),
        ("Recepção turística", R(85, 90)),
    ],
    "Aduana": [
        ("Condições da visita e da travessia", [2, 4, 5, 6, 8, 9]),
        ("Fluxo e filas", R(10, 19)),
        ("Conservação e limpeza", R(20, 25)),
        ("Informação e serviços", R(26, 29)),
        ("Inserção urbana e acessos", R(30, 39)),
        ("Acessibilidade", R(40, 47)),
        ("Sinalização", R(48, 58)),
        ("Segurança", R(59, 65)),
        ("Área de espera e órgãos presentes", R(66, 68)),
    ],
}

# campos que so identificam (o nome do ponto de onibus vira titulo do subgrupo)
PONTO_ONIBUS = {72: 1, 82: 2, 92: 3, 102: 4}

# Datas digitadas nas fichas divergem da data de envio em 71 de 97 casos
# (06_diario_de_campo.py); a Ponte da Amizade aparece como "mar. 7, 2026".
# Nao entram no texto: a cronologia de campo e a do diario.
OMITIR = ("Data", "Data e horário da visita", "Submission Date", "Registro",
          "Nome", "Município", "Município de coleta", "Ponto de análise",
          "Nome da aduana", "Nome do aeroporto")

# campos cujo valor e nome proprio e mantem a grafia
NOMES_PROPRIOS = ("País", "Principal atrativo", "Identificação do centro",
                  "Local definido", "Órgãos presentes", "Idiomas", "Ponto 1",
                  "Ponto 2", "Ponto 3", "Ponto 4", "Abrangência")

GRAFIA = {"Quadrupla": "quádrupla", "Tripla": "tripla", "Veiculos": "veículos",
          "sonorico": "sonoro", "táctil": "tátil", "Taxi": "táxi",
          "15-30 min": "15 a 30 min", "30-60 min": "30 a 60 min"}

UNIDADE_KM = ("Distância",)

FILTROS = ("Tem rua?", "Possui calçada?", "Possui ciclovia?",
           "Possui ponto de ônibus?", "Possui ponto de táxi?")

_cache: dict = {}


def tabela(formulario: str) -> pd.DataFrame:
    if formulario not in _cache:
        arq = sorted(JOTFORM.glob(ARQUIVOS[formulario]))[0]
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                _cache[formulario] = pd.read_csv(arq, encoding=enc,
                                                 low_memory=False)
                break
            except UnicodeDecodeError:
                continue
    return _cache[formulario]


def registro(formulario: str, linha_csv: int) -> pd.Series:
    """A linha da ficha; `linha_csv` segue a convencao do vinculo (i + 2)."""
    return tabela(formulario).iloc[int(linha_csv) - 2]


# ══════════════════════════════════════════════════════════════════════════════
# LEITURA DE UM CAMPO
# ══════════════════════════════════════════════════════════════════════════════
def _nome(col: str) -> str:
    """Nome legível do campo, sem as marcas do formulário."""
    n = re.sub(r"\.\d+$", "", col)
    n = re.sub(r"^\d+\.\s*", "", n)
    n = re.sub(r"\((?:LIKERT|likert|resposta múltipla|resposta única)\)", "", n)
    n = re.sub(r"\((?:ciclovia/ciclofaixa|ciclovia|faixa exclusiva \d|km)\)",
               "", n)
    n = re.sub(r"\(vertical = placas.*?\)", "", n)
    n = re.sub(r"^(?:Manejo de entorno|Acessibilidade):\s*", "", n)
    n = re.sub(r"^(?:Possui|Tem|Existência de)\s+", "", n, flags=re.I)
    n = re.sub(r"\s+ou não$", "", n.replace("?", "").strip())
    n = n.replace("sinaliação", "sinalização").replace("acento", "assento")
    n = n.replace("sufientes", "suficientes").replace("sonorico", "sonoro")
    n = n.replace("táctil", "tátil").replace("sinalização de Turismo",
                                             "sinalização turística")
    n = re.sub(r"(?i)(proteção) ao pedestres", r"\1 aos pedestres", n)
    n = n.replace("na saguão", "no saguão")
    n = re.sub(r"\s*\(.*?quando não exis.*?\)", "", n)
    n = re.sub(r"\s+", " ", n).strip(" :")
    if not n or n.startswith(("Wi-Fi", "QR", "PCD", "CAT")) or n[:2].isupper():
        return n
    return n[0].lower() + n[1:]


def _valor(col: str, v: str) -> str:
    """Grafia padronizada do valor."""
    for errado, certo in GRAFIA.items():
        v = v.replace(errado, certo)
    if any(col.startswith(p) for p in NOMES_PROPRIOS):
        return v
    return v[0].lower() + v[1:] if v and not v[:2].isupper() else v


def _escala(formulario: str, col: str):
    for frag, rot, direcao in ESCALAS.get(formulario, []):
        if frag.lower() in col.lower():
            return rot, direcao
    return None, None


def ler(formulario: str, col: str, valor):
    """Classifica um valor: ('nota', n, rótulo, direção) | ('sim'|'nao', ...) |
    ('texto', valor) | ('fora', valor) — ou None se vazio."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    v = str(valor).strip()
    if not v or v.lower() == "nan":
        return None
    m = re.match(r"^(\d)\s*-\s*(.+)$", v)                       # "4 - bom"
    if m:
        return ("nota", int(m.group(1)), m.group(2).strip().lower(), True)
    if v in ("Sim", "Não") or v.startswith(("Sim,", "Não,")):
        return ("sim" if v.startswith("Sim") else "nao", v)
    rot, direcao = _escala(formulario, col)
    num = pd.to_numeric(v.replace(",", "."), errors="coerce")
    if rot and pd.notna(num):
        n = int(num)
        if float(num) == n and 1 <= n <= len(rot):
            return ("nota", n, rot[n - 1], direcao)
        return ("fora", v)
    if pd.notna(num):
        txt = f"{num:g}".replace(".", ",")
        if col.startswith(UNIDADE_KM):
            txt += " km"
        return ("texto", txt)
    partes = [_valor(col, p.strip())
              for p in v.replace("\r", "").split("\n") if p.strip()]
    return ("texto", _lista(partes))


def _lista(itens, conj: str = "e") -> str:
    itens = [i for i in itens if i]
    if len(itens) <= 1:
        return "".join(itens)
    return ", ".join(itens[:-1]) + f" {conj} " + itens[-1]


# ══════════════════════════════════════════════════════════════════════════════
# NOTAS DE AVALIACAO
# ══════════════════════════════════════════════════════════════════════════════
def notas(formulario: str, reg: pd.Series) -> list[dict]:
    """Avaliações 1–5 normalizadas para 'maior = melhor', por bloco.

    Escalas sem direção (fluxo, movimentação) descrevem intensidade, não
    qualidade, e ficam de fora — pôr 'muito movimentado' numa régua de
    qualidade seria juízo que a ficha não faz.
    """
    cols = list(reg.index)
    saida = []
    for titulo, indices in BLOCOS[formulario]:
        for i in indices:
            if i >= len(cols):
                continue
            r = ler(formulario, cols[i], reg.iloc[i])
            if not r or r[0] != "nota" or r[3] is None:
                continue
            n = r[1] if r[3] else 6 - r[1]
            item = _nome(cols[i])
            if formulario == "Geral" and 72 <= i <= 111:
                k = max(k for k in PONTO_ONIBUS if k <= i)
                item = f"{item} — ponto de ônibus {PONTO_ONIBUS[k]}"
            elif formulario == "Geral" and 32 <= i <= 41:
                item = f"{item} — ciclovia"
            elif formulario == "Geral" and 112 <= i <= 121:
                item = f"{item} — táxi"
            elif formulario == "Geral" and 16 <= i <= 31:
                item = f"{item} — calçada"
            saida.append({"bloco": titulo, "item": item, "nota": n,
                          "rotulo": r[2], "invertida": not r[3]})
    return saida


# Colunas do formulário Geral que descrevem a via em si; reunidas, dizem que
# tipo de via o município oferece a quem circula.
VIA_COLS = {5: "cobertura", 6: "manutencao", 7: "faixas",
            9: "sinalizacao_transito", 13: "fluxo", 14: "tipos_de_fluxo"}
TIPOS_FLUXO = ["Veículos leves", "Carga", "Transporte coletivo",
               "Veículos turísticos"]
# as colunas que chegam como "4 - bom" e interessam pelo numero
VIA_ESCALA = ("fluxo", "manutencao")


def via(formulario: str, reg: pd.Series) -> dict:
    """Cobertura, manutencao, faixas, sinalizacao e composicao do fluxo."""
    if formulario != "Geral":
        return {}
    saida = {}
    for i, nome in VIA_COLS.items():
        if i >= len(reg):
            continue
        v = str(reg.iloc[i]).strip()
        if not v or v.lower() in ("nan", "none"):
            continue
        if nome == "tipos_de_fluxo":
            marcados = {x.strip() for x in v.splitlines() if x.strip()}
            saida[nome] = {t: (t in marcados) for t in TIPOS_FLUXO}
        elif nome in VIA_ESCALA:
            try:
                saida[nome] = int(float(v.split("-")[0].strip()))
            except ValueError:
                pass
        else:
            saida[nome] = v
    return saida


def presencas(formulario: str, reg: pd.Series) -> list[tuple[str, bool]]:
    """Itens de sim/não, na ordem do formulário."""
    cols = list(reg.index)
    saida, vistos = [], set()
    for _, indices in BLOCOS[formulario]:
        for i in indices:
            if i >= len(cols) or cols[i] in OMITIR or cols[i] == "Tem rua?":
                continue
            # itens de pontos de onibus 2..4 repetem os do ponto 1
            if formulario == "Geral" and 82 <= i <= 111:
                continue
            r = ler(formulario, cols[i], reg.iloc[i])
            if r and r[0] in ("sim", "nao"):
                nome = _nome(cols[i])
                # fila e ocorrencia, nao infraestrutura: um "sim" ali e
                # problema, e o sinal de marcado o leria como qualidade
                if nome.lower().startswith("formação de filas"):
                    continue
                if formulario == "Geral" and 72 <= i <= 81:
                    nome += " (ponto de ônibus)"
                elif formulario == "Geral" and 112 < i <= 121:
                    nome += " (táxi)"
                if nome not in vistos:
                    vistos.add(nome)
                    saida.append((nome, r[0] == "sim"))
    return saida
