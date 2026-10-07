# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
PROJETO UNESCO UNES 2369/2025 | ITAIPU PARQUETEC - TS.DTUR
================================================================================
MODULO COMUM: registro canonico dos 12 municipios e utilitarios de normalizacao.

PROBLEMA QUE RESOLVE:
    As camadas e planilhas do acervo usam grafias divergentes para o mesmo
    municipio ("Ponta Pora", "Ponta Pora ", "Ponta pora"; "Dionisio" x "Dionicio";
    "Bonito " com espaco; "Campo grande"). Qualquer agrupamento feito sobre o
    texto bruto produz contagens erradas.

SOLUCAO:
    Chave unica = codigo IBGE de 7 digitos. Os agrupamentos por municipio
    passam por `normalizar_municipio()`.

CAMINHOS:
    Todos os caminhos partem de RAIZ, lida da variavel de ambiente P4_DADOS.
    Sem ela, RAIZ e a pasta `dados/` na raiz do repositorio. A arvore abaixo
    de RAIZ reproduz a pasta do convenio ("Entregas/Produto 4/...",
    "Levantamentos e Análises/Produto 4/..."); o que vai em cada pasta esta em
    docs/mapa_de_dados.md.
================================================================================
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

# ==============================================================================
# CAMINHOS DO PROJETO
# ==============================================================================
RAIZ = Path(os.environ.get("P4_DADOS")
            or Path(__file__).resolve().parents[1] / "dados")
ENTREGAS = RAIZ / "Entregas" / "Produto 4"
ACERVO = RAIZ / "Levantamentos e Análises" / "Produto 4"
PRODUCAO = ENTREGAS / "produção"
CADERNO = PRODUCAO / "Caderno de informações por município"

DIR_DADOS = CADERNO / "02_Dados_Municipais"     # saidas por municipio e cache
DIR_GESTAO = CADERNO / "00_Gestao"              # relatorios de auditoria

CAMPO = ACERVO / "03_Pesquisa_de_Campo_Primaria"
JOTFORM = CAMPO / "01_Jotform_Bruto"
CAMADAS_QGIS = (ACERVO / "06_Dados_Processados_Pipeline" /
                "CNPJs_e_Atrativos_Clusters" / "camadas_qgis")
FOTOS_BASE = ENTREGAS / "Entrega 4.3"

# Sistemas de referencia
CRS_MAPA = 5880          # SIRGAS 2000 / Brazil Polyconic (metrico: distancias e areas)
CRS_DADOS = 4674         # SIRGAS 2000 geografico


# ==============================================================================
# REGISTRO CANONICO
# ==============================================================================
@dataclass(frozen=True)
class Municipio:
    ordem: int              # posicao no caderno
    codigo_ibge: int        # chave unica (validado na API de localidades do IBGE)
    nome: str               # grafia oficial IBGE
    uf: str
    slug: str               # nome de pasta (sem acento, sem espaco)
    pasta_campo: str        # nome da pasta em Entrega 4.3
    perfil: str             # papel esperado na rede turistica regional
    reg_imediata: str       # regiao geografica imediata (IBGE)
    reg_intermediaria: str  # regiao geografica intermediaria (IBGE)

    # Pertinencia tematica: define se a ausencia de um dado e lacuna real ou
    # simplesmente nao se aplica ao municipio. Sem isso, a auditoria acusa
    # "falta ficha de aeroporto" em municipio que nao tem aeroporto.
    linha_internacional: bool   # faz divisa com pais vizinho (terrestre ou fluvial)
    pais_vizinho: str           # pais(es) confrontante(s); vazio se nao houver
    tem_aerodromo: bool         # aerodromo com operacao de passageiros
    agua_navegavel: bool        # corpo d'agua com uso nautico relevante

    @property
    def nome_uf(self) -> str:
        return f"{self.nome} ({self.uf})"

    @property
    def dir_dados(self) -> Path:
        return DIR_DADOS / self.slug

    @property
    def dir_fotos(self) -> Path:
        return FOTOS_BASE / self.pasta_campo / "Fotos"


MUNICIPIOS: tuple[Municipio, ...] = (
    Municipio(1, 4108304, "Foz do Iguaçu", "PR", "01_Foz_do_Iguacu_PR",
              "07. Foz do Iguaçu - PR",
              "Polo de recepção e distribuição · portal de travessia",
              "Foz do Iguaçu", "Cascavel",
              True,  "Argentina e Paraguai", True,  True),
    Municipio(2, 4115804, "Medianeira", "PR", "02_Medianeira_PR",
              "10. Medianeira - PR",
              "Apoio e passagem no corredor BR-277",
              "Foz do Iguaçu", "Cascavel",
              False, "",                     False, True),
    Municipio(3, 4104501, "Capanema", "PR", "03_Capanema_PR",
              "12. Capanema - PR",
              "Nó de contato · acesso ao PNI pelo Rio Iguaçu",
              "Francisco Beltrão", "Cascavel",
              True,  "Argentina",            False, True),
    Municipio(4, 4102604, "Barracão", "PR", "04_Barracao_PR",
              "08. Barracão - PR",
              "Nó de contato trinacional (fronteira seca)",
              "Francisco Beltrão", "Cascavel",
              True,  "Argentina",            False, False),
    Municipio(5, 4205001, "Dionísio Cerqueira", "SC", "05_Dionisio_Cerqueira_SC",
              "09. Dionísio Cerqueira - SC",
              "Nó de contato trinacional (fronteira seca)",
              "São Miguel do Oeste", "Chapecó",
              True,  "Argentina",            False, False),
    Municipio(6, 4108809, "Guaíra", "PR", "06_Guaira_PR",
              "11. Guaíra - PR",
              "Portal de travessia · turismo fluvial",
              "Toledo", "Cascavel",
              True,  "Paraguai",             True,  True),
    Municipio(7, 5005681, "Mundo Novo", "MS", "07_Mundo_Novo_MS",
              "05. Mundo Novo - MS",
              "Portal de travessia (Ponte Ayrton Senna)",
              "Naviraí - Mundo Novo", "Dourados",
              True,  "Paraguai",             False, True),
    Municipio(8, 5006606, "Ponta Porã", "MS", "08_Ponta_Pora_MS",
              "03. Ponta Porã - MS",
              "Nó de contato conurbado (Pedro Juan Caballero)",
              "Ponta Porã", "Dourados",
              True,  "Paraguai",             True,  False),
    Municipio(9, 5006903, "Porto Murtinho", "MS", "09_Porto_Murtinho_MS",
              "04. Porto Murtinho - MS",
              "Portal da Rota Bioceânica",
              "Jardim", "Corumbá",
              True,  "Paraguai",             False, True),
    Municipio(10, 5003207, "Corumbá", "MS", "10_Corumba_MS",
              "01. Corumbá - MS",
              "Portal de travessia · polo do Pantanal",
              "Corumbá", "Corumbá",
              True,  "Bolívia",              True,  True),
    Municipio(11, 5002209, "Bonito", "MS", "11_Bonito_MS",
              "06. Bonito - MS",
              "Polo de recepção e distribuição (ecoturismo)",
              "Jardim", "Corumbá",
              False, "",                     True,  True),
    Municipio(12, 5002704, "Campo Grande", "MS", "12_Campo_Grande_MS",
              "02. Campo Grande - MS",
              "Polo distribuidor externo à linha, dentro da faixa",
              "Campo Grande", "Campo Grande",
              False, "",                     True,  False),
)

POR_CODIGO = {m.codigo_ibge: m for m in MUNICIPIOS}
POR_SLUG = {m.slug: m for m in MUNICIPIOS}


# ==============================================================================
# NORMALIZACAO
# ==============================================================================
def _chave(texto: str) -> str:
    """Reduz um nome a uma chave comparavel: sem acento, sem UF, sem pontuacao."""
    if texto is None:
        return ""
    t = str(texto).strip()
    # remove prefixos e sufixos de UF: "PR - Barracao", "Barracao - PR", "Barracao/PR"
    t = re.sub(r"^\s*(PR|MS|SC)\s*[-–/]\s*", "", t, flags=re.I)
    t = re.sub(r"\s*[-–/]\s*(PR|MS|SC)\s*$", "", t, flags=re.I)
    t = re.sub(r"\s*\((PR|MS|SC)\)\s*$", "", t, flags=re.I)
    # remove numeracao de pasta: "07. Foz do Iguacu"
    t = re.sub(r"^\s*\d{1,2}\s*[.\-]\s*", "", t)
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-zA-Z ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


# Grafias efetivamente encontradas no acervo, mapeadas ao codigo IBGE.
# A chave ja vem normalizada por _chave(), entao cobre variacoes de acento,
# caixa, espacos extras e prefixo/sufixo de UF.
_ALIASES: dict[str, int] = {}
for _m in MUNICIPIOS:
    _ALIASES[_chave(_m.nome)] = _m.codigo_ibge
# erros de grafia observados nas camadas e planilhas
_ALIASES.update({
    "dionicio cerqueira": 4205001,   # erro de grafia nas camadas 2, 3 e 4 do painel
    "medaneira": 4115804,            # erro de digitacao no Formulario Geral (1 registro)
})


def normalizar_municipio(texto: str) -> Municipio | None:
    """Devolve o Municipio canonico para qualquer grafia do acervo, ou None."""
    codigo = _ALIASES.get(_chave(texto))
    return POR_CODIGO.get(codigo) if codigo else None


# ==============================================================================
# COORDENADAS
# ==============================================================================
# A planilha georreferenciamento.xlsx foi preenchida em tres formatos distintos,
# conforme a equipe que lancou os dados:
#   (a) PR  - decimal separado: latitude = -25.294572 | longitude = -54.096401
#   (b) MS  - par completo na coluna latitude: "-20.464430, -54.552430" e
#             coluna longitude vazia  (42 das 69 linhas)
#   (c) dois registros em grau-minuto-segundo: 24°06'22.4"S | 54°14'20.7"W
# Ler apenas o formato (a) descarta 64% da planilha.

_DMS = re.compile(
    r"""(\d+(?:[.,]\d+)?)\s*[°º]\s*
        (?:(\d+(?:[.,]\d+)?)\s*['′]\s*)?
        (?:(\d+(?:[.,]\d+)?)\s*["″]\s*)?
        \s*([NSEWOLnsewol])?""",
    re.VERBOSE,
)


def _num(s: str) -> float | None:
    s = str(s).strip().replace(" ", "")
    if not s:
        return None
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    elif "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _dms(s: str) -> float | None:
    m = _DMS.search(str(s))
    if not m:
        return None
    grau = _num(m.group(1)) or 0.0
    minuto = _num(m.group(2) or 0) or 0.0
    seg = _num(m.group(3) or 0) or 0.0
    val = grau + minuto / 60 + seg / 3600
    if (m.group(4) or "").upper() in ("S", "W", "O"):
        val = -val
    return val


def parse_coordenadas(lat_bruta, lon_bruta=None) -> tuple[float | None, float | None]:
    """Extrai (lat, lon) de celulas em qualquer um dos tres formatos da planilha."""
    def _vazio(v):
        return v is None or (isinstance(v, float) and v != v) or str(v).strip() == ""

    lat_s = "" if _vazio(lat_bruta) else str(lat_bruta).strip()
    lon_s = "" if _vazio(lon_bruta) else str(lon_bruta).strip()

    # formato (c): grau-minuto-segundo
    if re.search(r"[°º'\"′″]", lat_s):
        return _dms(lat_s), (_dms(lon_s) if lon_s else None)

    # formato (b): par completo na celula de latitude
    if lon_s == "" and "," in lat_s:
        partes = [p for p in re.split(r"[;,]\s*", lat_s) if p.strip()]
        if len(partes) == 2:
            a, b = _num(partes[0]), _num(partes[1])
            if a is not None and b is not None:
                return a, b
        return None, None

    # formato (a): decimal em colunas separadas
    return _num(lat_s), (_num(lon_s) if lon_s else None)


def coordenada_plausivel(lat, lon) -> bool:
    """Confere se a coordenada cai no envelope do recorte do estudo."""
    if lat is None or lon is None:
        return False
    return -34.0 <= lat <= -5.0 and -62.0 <= lon <= -44.0


# ==============================================================================
# DATAS EM PORTUGUES (Jotform)
# ==============================================================================
# O Jotform exporta o carimbo de envio por extenso e em portugues:
#     "terça-feira, agosto 18, 2026 11:45"
# pandas.to_datetime nao le esse formato e devolve NaT, o que faz a coluna
# parecer vazia. E o registro mais confiavel de quando cada ficha foi
# preenchida - mais do que o campo "Data", digitado a mao e com erros.
_MESES_PT = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7,
    "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}

_RE_DATA_PT = re.compile(
    r"(?:[a-zç-]+-feira|s[áa]bado|domingo)?\s*,?\s*"
    r"([a-zç]+)\.?\s+(\d{1,2}),?\s+(\d{4})"
    r"(?:\s+(\d{1,2}):(\d{2}))?",
    re.IGNORECASE,
)


def parse_data_pt(valor):
    """Converte o carimbo do Jotform em datetime. Devolve None se nao reconhecer."""
    from datetime import datetime
    if valor is None or (isinstance(valor, float) and valor != valor):
        return None
    if hasattr(valor, "year"):
        return valor
    m = _RE_DATA_PT.search(str(valor).strip())
    if not m:
        return None
    mes = _MESES_PT.get(_chave(m.group(1)))
    if not mes:
        return None
    dia, ano = int(m.group(2)), int(m.group(3))
    hora = int(m.group(4)) if m.group(4) else 0
    minuto = int(m.group(5)) if m.group(5) else 0
    try:
        return datetime(ano, mes, dia, hora, minuto)
    except ValueError:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# ROTULO CURTO DE PONTO DE AFERICAO
# ══════════════════════════════════════════════════════════════════════════════
_LIMPAR = [
    (r"\s*\((?:rodovia|via)\s+(?:federal|estadual|municipal)\)", ""),
    (r"\s*,?\s+com\s+", " × "),
    (r"\bAvenida\b", "Av."),
    (r"\bRodovia\s+BR[- ]?(\d+)", r"BR-\1"),
    (r"\bAv\.\s+das\s+Cataratas\b", "Av. Cataratas"),
    (r"\bAv\.\s+Perimetral\s+Leste\b", "Perimetral Leste"),
    # referencia de ponto de apoio: a cruzamento ja identifica o local
    (r"\s*\(\s*pr[óo]ximo ao Shopping[^)]*\)", ""),
    (r"(?<=\w)\s+-\s+(?=\w)", " — "),
    (r"rotas para atrativos tur[íi]stico e ACTs", "acesso aos atrativos"),
    (r",?\s*rodovia de acesso a fronteira e [àa]s? ACTs",
     " — acesso à fronteira"),
    (r"\s*\(Ponte da Fraternidade\)", ""),        # apelido, não distingue
    (r"\bEsta[çc][ãa]o\s+Rodovi[áa]ria\b", "Rodoviária"),
    (r"\bTerminal\s+Rodovi[áa]rio\b", "Rodoviária"),
    (r"\bAeroporto\s+Internacional\b", "Aeroporto Intern."),
    (r"\bPonte\s+Internacional\b", "Ponte Intern."),
    (r"\bPonte Intern\. sobre o (Rio [^,(]+)", r"Ponte do \1"),
    (r"\bInspetoria da Receita Federal do Brasil\b", "Receita Federal"),
    (r"\bAlf[âa]ndega da Receita Federal do Brasil\b", "Alfândega RFB"),
    (r"\bCentro de Atendimento ao Turista\b", "CAT"),
    (r"\s{2,}", " "),
]


def rotulo_curto(nome: str, municipio: str | None = None, n: int = 42) -> str:
    """Nome do ponto encurtado para listagens, sem perder o que o
    identifica.

    Os nomes da sintese de campo sao descritivos e longos — "BR-277 (rodovia
    federal), com Avenida Perimetral Leste (rodovia municipal)". Em tabelas
    e listas comparativas eles nao cabem. O que se remove e o que nao
    distingue: a qualificacao da via, o nome do municipio (ja implicito no
    recorte) e o aposto que repete o que o nome ja diz
    ("Praca Naipi e Taroba: Praca de lazer regiao central"). O que distingue
    — o parentese que diferencia dois pontos de mesmo nome — fica.
    """
    s = re.sub(r"\s+", " ", str(nome or "")).strip()
    if municipio:
        s = re.sub(rf"\s+(?:de|em|d[oa])\s+{re.escape(municipio)}\b", "", s,
                   flags=re.I)
    # aposto depois de dois-pontos: repete o que o nome ja diz
    s = re.sub(r"^([^:]{6,}?):\s+.*$", r"\1", s)
    for padrao, troca in _LIMPAR:
        s = re.sub(padrao, troca, s, flags=re.I)
    s = s.strip(" ,;")
    return s if len(s) <= n else s[: n - 1].rstrip(" ,;(") + "…"

# ══════════════════════════════════════════════════════════════════════════════
# CIDADES FRONTEIRIÇAS
# ══════════════════════════════════════════════════════════════════════════════
# As cidades do outro lado da linha, em frente aos municípios do estudo. Não
# são "cidade de referência": a fronteira é parte da experiência turística e
# do fluxo diário, e o tempo que as separa é minutos, não horas.
#
# (nome, lon, lat, municípios do estudo que ela faz fronteira)
# Coordenadas conferidas contra o polígono do país e contra a divisa do
# município gêmeo — todas caem no país certo e a menos de 8 km da divisa.
FRONTEIRICAS: list[tuple[str, float, float, tuple[str, ...]]] = [
    ("Ciudad del Este (PY)",      -54.6110, -25.5097, ("Foz do Iguaçu",)),
    ("Puerto Iguazú (AR)",        -54.5736, -25.5991, ("Foz do Iguaçu",)),
    ("Salto del Guairá (PY)",     -54.3064, -24.0561, ("Guaíra", "Mundo Novo")),
    ("Pedro Juan Caballero (PY)", -55.7333, -22.5472, ("Ponta Porã",)),
    ("Carmelo Peralta (PY)",      -57.9139, -21.7167, ("Porto Murtinho",)),
    ("Puerto Quijarro (BO)",      -57.7667, -19.0333, ("Corumbá",)),
    ("Puerto Suárez (BO)",        -57.8014, -18.9619, ("Corumbá",)),
    ("Bernardo de Irigoyen (AR)", -53.6469, -26.2547,
     ("Barracão", "Dionísio Cerqueira")),
]


def fronteiricas_de(municipio: str) -> list[tuple[str, float, float]]:
    """As cidades em frente a este município."""
    return [(n, lon, lat) for n, lon, lat, gemeos in FRONTEIRICAS
            if municipio in gemeos]


if __name__ == "__main__":
    # Conferencia do registro e da normalizacao: python comum.py
    import io
    import sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print(f"{len(MUNICIPIOS)} municipios no registro canonico\n")
    for m in MUNICIPIOS:
        print(f"  {m.ordem:>2}. {m.codigo_ibge}  {m.nome_uf:<26} {m.slug}")
    print("\nTeste de normalizacao das grafias divergentes do acervo:")
    testes = ["Ponta Porã", "Ponta Porã ", "Ponta pora", "Dionísio Cerqueira",
              "Dionício Cerqueira", "Bonito ", "Campo grande", "PR - Barracão",
              "SC - Dionísio Cerqueira", "07. Foz do Iguaçu - PR", "Inexistente"]
    for t in testes:
        m = normalizar_municipio(t)
        print(f"  {t!r:<30} -> {m.nome_uf if m else 'NAO RECONHECIDO'}")
