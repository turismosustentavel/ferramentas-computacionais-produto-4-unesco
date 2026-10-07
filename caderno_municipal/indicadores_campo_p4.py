# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMAÇÕES POR MUNICÍPIO | PRODUTO 4
INDICADORES DOS PONTOS AFERIDOS EM CAMPO
================================================================================
Calcula, por município, os indicadores que resultam das fichas de campo
(Jotform: formulários Geral, Rodoviária, Aeroporto e Aduana) depois de lidas
por `fichas_p4` e reunidas por ponto aferido.

INDICADORES
    Presença e ausência (itens de sim/não, agrupados por `presencas_p4`)
        presencas_nos_pontos   grade item × ponto para os pontos de chegada
                               (rodoviária, aeroporto, aduana), para os pontos
                               de via (formulário Geral) e para as aduanas;
                               conta os itens ausentes em TODOS os pontos
                               (nenhum "sim" e ao menos um "não").
        itens_do_terminal      itens próprios do formulário da rodoviária ou do
                               aeroporto, com a contagem de ausências.
        resumo_rodoviaria      ausências por etapa de uso do terminal, etapa
                               que concentra ao menos metade delas e usos
                               afetados (espera, orientação, CAT,
                               estacionamento, fraldário, caixa eletrônico).
        resumo_aeroporto       ausências por natureza (recepção de grupos,
                               circulação vertical, vigilância com câmeras,
                               demais), proporção de ausências e serviços de
                               apoio ao visitante presentes.
        resumo_aduanas         itens ausentes em todos os postos, itens que
                               diferem entre postos e posto com mais ausências.
        taxi_e_locadora_na_chegada
                               pontos de chegada com e sem ponto de táxi e
                               locadora de veículos no aeroporto.
    Avaliação (médias por dimensão e por bloco, de 1 a 5, maior = melhor)
        notas_por_ponto        média de cada ponto em cada dimensão e classe
                               de 1 a 5 (média arredondada).
        resumo_avaliacao_chegada
                               três dimensões de menor média e duas de maior.
        resumo_avaliacao_interna
                               via × calçada (diferença mínima de 0,2 ponto
                               para haver vantagem) e os dois menores
                               registros por ponto.
    Caracterização da via
        caracterizacao_das_vias
                               cobertura, faixas, manutenção, sinalização,
                               intensidade e composição do fluxo de cada ponto
                               do formulário Geral, com a classe funcional da
                               via no OpenStreetMap (`classe_via_p4`).
        resumo_caracterizacao  pavimentação, pista simples, fluxo no grau
                               máximo, presença de carga e de veículos de
                               turismo (carga em ao menos metade dos pontos).
        vias_de_chegada        pista, manutenção, acostamento, iluminação e
                               sinalização (trânsito, turismo e pedestres) das
                               vias de chegada (grupo "chegada", formulário
                               Geral).
        resumo_vias_de_chegada amplitude da manutenção e ausências comuns a
                               todas as vias.

FONTES
    Fichas de campo do Produto 4 (Itaipu Parquetec, 2026); classe funcional da
    via: OpenStreetMap (etiqueta `highway`).

ENTRADAS (relativas a P4_DADOS)
    Entregas/Produto 4/produção/Caderno de informações por município/
    02_Dados_Municipais/<slug>/
        fichas_<slug>.json            (avaliacao_pontos_p4.py)
            índice das fichas por ponto ("Ponto #n": formulário, presenças,
            caracterização da via)
        metricas_matrizes_<slug>.json (avaliacao_pontos_p4.py)
            médias de avaliação por ponto, dimensão e bloco ("grade",
            "chegada", "interna")
        camadas_internas_<slug>.gpkg  (deslocamento_interno_p4.py)
            camada "pontos_afericao" (coordenadas dos pontos)
        metricas_contexto_<slug>.json (contexto_p4.py)
            só a lista de rotas aéreas internacionais (resumo do aeroporto)
    Módulos do repositório: presencas_p4 (vocabulário e grade de presença),
    fichas_p4 (tipos de fluxo), classe_via_p4 (classe funcional da via, com
    cache em 02_Dados_Municipais/cache/osm_classe_via_<slug>.json).

ORDEM
    Depois de avaliacao_pontos_p4.py, deslocamento_interno_p4.py e
    contexto_p4.py.

SAÍDAS
    02_Dados_Municipais/indicadores_campo.xlsx, uma aba por tema, uma ou mais
    linhas por município.

COMO EXECUTAR
    python indicadores_campo_p4.py                 os doze municípios
    python indicadores_campo_p4.py 07_Mundo_Novo_MS
    python indicadores_campo_p4.py --saida <pasta> grava em outra pasta
================================================================================
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import classe_via_p4 as cvia                                     # noqa: E402
import fichas_p4                                                 # noqa: E402
import presencas_p4 as pp                                        # noqa: E402
from comum import DIR_DADOS, MUNICIPIOS, POR_SLUG                # noqa: E402


# ══════════════════════════════════════════════════════════════════════════════
# LEITURA
# ══════════════════════════════════════════════════════════════════════════════
def _json(p: Path) -> dict:
    return json.loads(p.read_text("utf-8")) if p.exists() else {}


def arquivo_fichas(m) -> Path:
    return DIR_DADOS / m.slug / f"fichas_{m.slug}.json"


def arquivo_avaliacoes(m) -> Path:
    return DIR_DADOS / m.slug / f"metricas_matrizes_{m.slug}.json"


def arquivo_pontos(m) -> Path:
    return DIR_DADOS / m.slug / f"camadas_internas_{m.slug}.gpkg"


def arquivo_contexto(m) -> Path:
    return DIR_DADOS / m.slug / f"metricas_contexto_{m.slug}.json"


def carregar_fichas(m) -> dict:
    """{"Ponto #n": {formulario, ponto, presencas, via, ...}}."""
    return _json(arquivo_fichas(m))


def carregar_avaliacoes(m) -> dict:
    """Médias de avaliação: "grade" (por ponto), "chegada" e "interna"."""
    return _json(arquivo_avaliacoes(m))


def coordenadas_dos_pontos(m) -> dict[int, tuple[float, float]]:
    """{número do ponto: (lat, lon)} em WGS 84 (EPSG:4326)."""
    try:
        import geopandas as gpd
        g = gpd.read_file(arquivo_pontos(m), layer="pontos_afericao").to_crs(4326)
        return {int(r.numero): (r.geometry.y, r.geometry.x)
                for r in g.itertuples()}
    except Exception:                                            # noqa: BLE001
        return {}


def rota_aerea_internacional(m) -> bool:
    """A malha aérea regular do município inclui rota internacional?"""
    ae = _json(arquivo_contexto(m)).get("aereo") or {}
    return bool(ae.get("internacionais") or [])


# ══════════════════════════════════════════════════════════════════════════════
# PONTOS POR FORMULÁRIO
# ══════════════════════════════════════════════════════════════════════════════
def numeros_de(fichas: dict, *formularios: str) -> list[int]:
    """Números dos pontos aferidos com algum desses formulários.

    O formulário é a autoridade, e não o nome do ponto: o número muda de
    município para município.
    """
    return sorted(
        int(re.search(r"(\d+)", k).group(1))
        for k, v in fichas.items()
        if any(f in str(v.get("formulario", "")) for f in formularios))


def numero_do_formulario(fichas: dict, formulario: str) -> int | None:
    """O primeiro ponto aferido com exatamente aquele formulário."""
    for chave_p, reg in fichas.items():
        if (reg or {}).get("formulario") == formulario:
            d = "".join(c for c in str(chave_p) if c.isdigit())
            if d:
                return int(d)
    return None


# ══════════════════════════════════════════════════════════════════════════════
# PRESENÇA E AUSÊNCIA
# ══════════════════════════════════════════════════════════════════════════════
def presencas_nos_pontos(fichas: dict, temas, numeros: list[int]) -> dict | None:
    """Grade item × ponto e contagem dos itens ausentes em todos os pontos.

    Estado de cada célula: True (existe), False (não existe) ou None (o
    formulário daquele ponto não pergunta pelo item). Um item é "ausente em
    todos" quando nenhum ponto o tem e ao menos um registra a falta.
    """
    numeros = [n for n in numeros if any(
        str(n) == "".join(c for c in str(o) if c.isdigit())
        for o in fichas)]
    if not numeros:
        return None
    g = pp.grade(fichas, temas, numeros)
    linhas = g["linhas"]
    if not linhas:
        return None
    faltam_todos = 0
    for _, _, estados in linhas:
        vazia = all(e is False for e in estados if e is not None) and \
            any(e is False for e in estados)
        if vazia:
            faltam_todos += 1
    return {"pontos": numeros, "itens": len(linhas),
            "ausentes_em_todos": faltam_todos,
            "linhas": [{"tema": tm, "item": r, "estados": e}
                       for tm, r, e in linhas]}


def ausentes_em_todos(bloco: dict | None) -> list[str]:
    """Itens que nenhum dos pontos do bloco tem (e ao menos um registra)."""
    if not bloco:
        return []
    return [l["item"] for l in bloco["linhas"]
            if any(e is False for e in l["estados"])
            and all(e is not True for e in l["estados"])]


def itens_do_terminal(fichas: dict, formulario: str, temas) -> dict | None:
    """Itens próprios do formulário de um terminal, com as ausências."""
    n = numero_do_formulario(fichas, formulario)
    if n is None:
        return None
    g = pp.grade(fichas, temas, [n])
    linhas = [(tema, rot, est[0]) for tema, rot, est in g["linhas"]]
    if not linhas:
        return None
    faltam = sum(1 for _, _, e in linhas if e is False)
    return {"ponto": n, "itens": len(linhas), "ausentes": faltam,
            "linhas": [{"tema": tm_, "item": r_, "estado": e}
                       for tm_, r_, e in linhas]}


# Etapas de uso da rodoviária (temas de `presencas_p4.RODOVIARIA`) em que
# a concentração das ausências é verificada.
ETAPAS_RODOVIARIA = ("Orientação de quem embarca", "Comprar e despachar",
                     "Esperar", "Comércio e serviços", "Acesso e vigilância")

# Uso do terminal afetado pela ausência de cada item (nomes em minúsculas).
USOS_RODOVIARIA = {
    "espera_sem_apoio": {"guarda-volumes", "autoatendimento de passagens",
                         "banheiros", "bebedouro",
                         "lixeiras na área de espera",
                         "cobertura na área de espera", "proteção climática"},
    "orientacao_no_guiche": {"identificação das plataformas",
                             "informações sobre horários",
                             "informações sobre linhas",
                             "painéis de partidas e chegadas",
                             "placas de orientação interna"},
    "sem_orientacao_turistica": {"centro de atendimento ao turista"},
    "sem_estacionamento": {"estacionamento para automóveis"},
    "sem_fraldario": {"fraldário"},
    "sem_caixa_eletronico": {"caixa eletrônico"},
}


def resumo_rodoviaria(itens: dict | None) -> dict | None:
    """Ausências do terminal rodoviário por etapa de uso."""
    if not (itens or {}).get("linhas"):
        return None
    lr = itens["linhas"]
    falta = [x["item"].lower() for x in lr if x["estado"] is False]
    temas = list(dict.fromkeys(x["tema"] for x in lr))

    def _itens(tema, estado):
        return [x["item"].lower() for x in lr
                if x["tema"] == tema and x["estado"] is estado]

    acesso = next((t for t in temas if "cesso" in t), None)
    saida = {
        "ponto": itens.get("ponto"),
        "itens": len(lr),
        "ausentes": len(falta),
        "itens_ausentes": falta,
        "tema_inicial": temas[0],
        "presentes_no_tema_inicial": _itens(temas[0], True),
        "tema_de_acesso": acesso,
        "presentes_no_tema_de_acesso": _itens(acesso, True) if acesso else [],
        "tema_com_mais_ausencias": None,
        "ausencias_no_tema": None,
        "ausencias_concentradas": False,
    }
    if falta:
        por_tema: dict = {}
        for x in lr:
            if x["estado"] is False:
                por_tema[x["tema"]] = por_tema.get(x["tema"], 0) + 1
        t_max = max(por_tema, key=por_tema.get)
        nf = len(falta)
        saida.update(
            tema_com_mais_ausencias=t_max,
            ausencias_no_tema=por_tema[t_max],
            # ao menos a metade das ausências numa só etapa
            ausencias_concentradas=bool(nf > 1 and por_tema[t_max] * 2 >= nf
                                        and t_max in ETAPAS_RODOVIARIA))
    for uso, conjunto in USOS_RODOVIARIA.items():
        saida[uso] = bool(set(falta) & conjunto)
    return saida


def resumo_aeroporto(itens: dict | None,
                     rota_internacional: bool) -> dict | None:
    """Ausências do aeroporto pela natureza, e o apoio ao visitante.

    `rota_internacional`: a malha aérea regular (ANAC) inclui rota
    internacional. Sem ela, o item "voos internacionais" da ficha não conta
    como serviço de apoio.
    """
    if not (itens or {}).get("linhas"):
        return None
    la = itens["linhas"]
    falta = [x["item"].lower() for x in la if x["estado"] is False]
    tem = {x["item"].lower() for x in la if x["estado"] is True}
    avaliados = len([x for x in la if x["estado"] is not None])
    nfa = len(falta)
    recep = [x for x in falta if "receptiv" in x or "excurs" in x]
    circ = [x for x in ("elevador", "escada rolante") if x in falta]
    vig = "vigilância visível" in falta and "câmeras" in tem
    resto = [x for x in falta if x not in recep and x not in circ
             and not (vig and x == "vigilância visível")]
    apoio = [x for x in (("voos internacionais" if rota_internacional
                          else None),
                         "serviço de câmbio", "locadora de veículos",
                         "guarda-volumes", "autoatendimento de check-in")
             if x and x in tem]
    return {
        "ponto": itens.get("ponto"),
        "itens_avaliados": avaliados,
        "ausentes": nfa,
        "itens_ausentes": falta,
        # até um terço de ausências: o terminal atende à maior parte
        "ausencias_ate_um_terco": nfa * 3 <= avaliados,
        "ausentes_recepcao_de_grupos": recep,
        "ausentes_circulacao_vertical": circ,
        "vigilancia_so_por_cameras": vig,
        "demais_ausentes": resto,
        "servicos_de_apoio": apoio,
    }


def resumo_aduanas(presencas_aduana: dict | None,
                   avaliacoes: dict) -> dict | None:
    """O que falta em todos os postos de fronteira e o que os distingue."""
    aduanas = [g for g in avaliacoes.get("grade", [])
               if "Aduana" in str(g.get("formulario", ""))]
    if not aduanas:
        return None
    pa = presencas_aduana or {}
    lin = pa.get("linhas") or []
    ns = list(pa.get("pontos") or [a["numero"] for a in aduanas])
    saida = {"postos_avaliados": [a["numero"] for a in aduanas],
             "pontos_na_grade": ns,
             "ausentes_em_todos": [],
             "itens_que_diferem": 0,
             "posto_com_mais_ausencias": None,
             "ausentes_no_posto": [],
             "outro_posto": None}
    if not lin:
        return saida
    saida["ausentes_em_todos"] = [
        l["item"].lower() for l in lin
        if any(e is False for e in l["estados"])
        and all(e is not True for e in l["estados"])]
    difere = [l for l in lin
              if len({e for e in l["estados"] if e is not None}) > 1]
    saida["itens_que_diferem"] = len(difere)
    if difere and len(ns) > 1:
        falhas = {n: sum(1 for l in difere if l["estados"][i] is False)
                  for i, n in enumerate(ns)}
        pior = max(falhas, key=falhas.get)
        saida["posto_com_mais_ausencias"] = pior
        saida["outro_posto"] = next((n for n in ns if n != pior), None)
        saida["ausentes_no_posto"] = [
            l["item"].lower() for l in difere
            if l["estados"][ns.index(pior)] is False]
    return saida


def taxi_e_locadora_na_chegada(presencas_terminais: dict | None,
                               aeroporto: dict | None,
                               avaliacoes: dict) -> dict:
    """Ponto de táxi nos pontos de chegada e locadora no aeroporto."""
    pt = presencas_terminais or {}
    form = {g["numero"]: g.get("formulario", "")
            for g in avaliacoes.get("grade", [])}
    tx = next((l["estados"] for l in pt.get("linhas", [])
               if l["item"] == "Ponto de táxi"), [])
    com = [n for n, e in zip(pt.get("pontos", []), tx) if e is True]
    sem = [n for n, e in zip(pt.get("pontos", []), tx) if e is False]
    loc = next((l["estado"] for l in (aeroporto or {}).get("linhas", [])
                if "ocadora" in l["item"]), None)
    return {"pontos_com_taxi": com,
            "formularios_com_taxi": [form.get(n) for n in com],
            "pontos_sem_taxi": sem,
            "locadora_no_aeroporto": loc}


# ══════════════════════════════════════════════════════════════════════════════
# AVALIAÇÃO (ESCALA DE 1 A 5)
# ══════════════════════════════════════════════════════════════════════════════
def notas_por_ponto(avaliacoes: dict, grupo: str) -> dict | None:
    """Média de cada ponto do grupo em cada dimensão (ou bloco) avaliada.

    `classe` é a média arredondada ao inteiro (1 péssimo … 5 ótimo), com o
    arredondamento do Python (metade para o par).
    """
    grade = [g for g in avaliacoes.get("grade", []) if g["grupo"] == grupo]
    if not grade:
        return None
    campo = (avaliacoes.get(grupo) or {}).get("tipo_de_coluna", "dimensao")
    cols = (avaliacoes.get(grupo) or {}).get("colunas") or []
    cols = [c for c in cols if any(c in g[campo] for g in grade)]
    if not cols:
        return None
    notas = [{"numero": g["numero"], "nome": g["nome"], "dimensao": c,
              "media": v, "classe": int(round(v))}
             for c in cols for g in grade
             for v in [g[campo].get(c)] if v is not None]
    return {"pontos": len(grade), "dimensoes": cols, "notas": notas}


def resumo_avaliacao_chegada(avaliacoes: dict) -> dict:
    """As três dimensões de menor média e as duas de maior, na chegada.

    A ordem é a de `media_por_coluna`, crescente pela média.
    """
    mc2 = avaliacoes.get("chegada") or {}
    med = list((mc2.get("media_por_coluna") or {}).items())
    return {"menores": med[:3], "maiores": med[-2:]}


# Diferença mínima, na escala de 1 a 5, para considerar a via mais bem
# avaliada que a calçada (ou o contrário).
FOLGA_VIA_CALCADA = 0.2


def resumo_avaliacao_interna(avaliacoes: dict) -> dict:
    """Via × calçada nos pontos de circulação interna e os menores registros."""
    mc3 = avaliacoes.get("interna") or {}
    mpc = mc3.get("media_por_coluna") or {}
    mv = mpc.get("A via")
    mcal = mpc.get("Calçada, travessia e acessibilidade")
    vantagem = None
    if mv is not None and mcal is not None:
        if mv - mcal >= FOLGA_VIA_CALCADA:
            vantagem = "via"
        elif mcal - mv >= FOLGA_VIA_CALCADA:
            vantagem = "calçada"
        else:
            vantagem = "equilíbrio"
    # os dois menores registros, reunidos por ponto, com os elementos da
    # coluna separados ("Calçada, travessia e acessibilidade" -> três)
    por_ponto: dict = {}
    for r in (mc3.get("piores") or [])[:2]:
        por_ponto.setdefault(r["ponto"], []).extend(
            re.sub(r"^a ", "", x) for x in
            re.split(r", | e ", r["coluna"].lower()))
    return {"pontos": mc3.get("pontos"),
            "um_ponto": (mc3.get("pontos") or 0) == 1,
            "media_via": mv, "media_calcada": mcal,
            "vantagem": vantagem,
            "menores_avaliacoes": list(por_ponto.items())}


# ══════════════════════════════════════════════════════════════════════════════
# CARACTERIZAÇÃO DA VIA
# ══════════════════════════════════════════════════════════════════════════════
def caracterizacao_das_vias(m, fichas: dict, avaliacoes: dict,
                            coordenadas: dict, classes=None) -> list | None:
    """Uma linha por ponto do formulário Geral: a via vista em campo e a
    classe funcional dela no OpenStreetMap.

    `classes`: função (slug, {número: (lat, lon)}) -> {"n": {"rotulo": …}};
    por padrão, `classe_via_p4.classes`. Se a consulta falhar, a classe fica
    vazia.
    """
    longo = {g["numero"]: g.get("nome_texto") or g["nome"]
             for g in avaliacoes.get("grade", [])}
    pontos = []
    for ordem, f in sorted(fichas.items(),
                           key=lambda kv: int(re.search(r"(\d+)",
                                                        kv[0]).group(1))):
        v = f.get("via") or {}
        if not v:
            continue
        n = int(re.search(r"(\d+)", ordem).group(1))
        nome = str(longo.get(n, f.get("ponto")))
        # "CAT (CAT)" -> "CAT"; parêntese órfão sai
        nome = re.sub(r"^(.+?) \(\1\)$", r"\1", nome)
        if nome.count(")") > nome.count("("):
            nome = nome.rstrip(")")
        pontos.append({"numero": n, "nome": nome, **v})
    if not pontos:
        return None
    classes = classes or cvia.classes
    try:
        cls = classes(m.slug, {p["numero"]: coordenadas[p["numero"]]
                               for p in pontos
                               if p["numero"] in coordenadas})
    except Exception as e:                                   # noqa: BLE001
        print(f"   classe da via indisponível: {e}")
        cls = {}
    for p in pontos:
        p["classe"] = (cls.get(str(p["numero"])) or {}).get("rotulo", "")
    return pontos


# Intensidade do fluxo a partir da qual o ponto está no grau máximo (1 a 5).
FLUXO_MAXIMO = 5


def resumo_caracterizacao(pontos: list | None) -> dict | None:
    """Pavimentação, pista simples, fluxo e composição nos pontos de via."""
    if not pontos:
        return None
    n = len(pontos)
    pav = {str(p.get("cobertura", "")).lower() for p in pontos}
    classes = [p["classe"] for p in pontos if p.get("classe")]
    simples = [p for p in pontos
               if str(p.get("faixas", "")).lower() == "simples"]
    pico = [p for p in pontos if (p.get("fluxo") or 0) >= FLUXO_MAXIMO]

    def _com(tipo):
        return [p for p in pontos if (p.get("tipos_de_fluxo") or {}).get(tipo)]

    carga, tur = _com("Carga"), _com("Veículos turísticos")
    return {
        "pontos": n,
        "todas_pavimentadas":
            pav <= {"asfalto", "paralelepipedo", "paralelepípedo"},
        # classe do primeiro e do último ponto (ordem do número), quando os
        # pontos não têm todos a mesma classe
        "classe_primeiro_ponto": classes[0] if len(set(classes)) > 1 else None,
        "classe_ultimo_ponto": classes[-1] if len(set(classes)) > 1 else None,
        "pontos_pista_simples": [p["numero"] for p in simples],
        "pontos_fluxo_maximo": [p["numero"] for p in pico],
        "pista_simples_com_fluxo_maximo":
            bool(simples and pico and simples[0]["numero"] == pico[0]["numero"]),
        "pontos_com_carga": len(carga),
        "pontos_com_veiculos_de_turismo": len(tur),
        "carga_em_metade_ou_mais": len(carga) * 2 >= n,
    }


_FAIXAS = {"simples": "simples", "dupla": "dupla", "tripla": "tripla",
           "quadrupla": "quádrupla", "quádrupla": "quádrupla"}
# a planilha de campo grafa a cobertura sem acento
_COBERTURA = {"paralelepipedo": "Paralelepípedo", "terra batida": "Terra batida",
              "asfalto": "Asfalto"}
_SINAL = {"sinalização vertical e horizontal": "vertical e horizontal",
          "sinalização vertical": "só vertical",
          "sinalização horizontal": "só horizontal"}


def _sim_nao(fichas_ponto: dict, item: str):
    """True/False se a ficha do ponto pergunta pelo item; None se não."""
    for nome, tem in fichas_ponto.get("presencas", []):
        if str(nome).strip().lower() == item:
            return bool(tem)
    return None


def vias_de_chegada(fichas: dict, avaliacoes: dict) -> list[dict]:
    """As vias de chegada (grupo "chegada", formulário Geral), uma linha cada.

    Presenças: True (existe), False (não existe), None (o formulário não
    cobriu o item naquele ponto).
    """
    por_numero = {}
    for ordem, f in fichas.items():
        achado = re.search(r"(\d+)", str(ordem))
        if achado:
            por_numero[int(achado.group(1))] = f
    linhas = []
    for g in avaliacoes.get("grade", []):
        if g.get("grupo") != "chegada" or g.get("formulario") != "Geral":
            continue
        f = por_numero.get(g["numero"]) or {}
        v = f.get("via") or {}
        cru = str(v.get("sinalizacao_transito") or "").strip()
        sinal = _SINAL.get(cru.lower(), cru[:1].lower() + cru[1:])
        linhas.append({
            "numero": g["numero"],
            "nome": g["nome"],
            "cobertura": (_COBERTURA.get(str(v.get("cobertura", "")).strip()
                                         .lower(),
                                         str(v.get("cobertura") or ""))
                          or None),
            "faixas": _FAIXAS.get(str(v.get("faixas", "")).strip().lower()),
            "manutencao": v.get("manutencao") or None,
            "acostamento": _sim_nao(f, "acostamento"),
            "iluminacao": _sim_nao(f, "iluminação"),
            "sinalizacao_transito": sinal or None,
            "sinalizacao_turistica": _sim_nao(f, "sinalização turística"),
            "sinalizacao_pedestres": _sim_nao(f, "sinalização para pedestres"),
        })
    return linhas


def resumo_vias_de_chegada(linhas: list[dict]) -> dict | None:
    """Amplitude da manutenção e ausências comuns às vias de chegada."""
    if not linhas:
        return None
    n = len(linhas)
    notas = [l["manutencao"] for l in linhas if l["manutencao"]]
    sem_tur = [l for l in linhas if l["sinalizacao_turistica"] is False]
    return {
        "vias": n,
        "manutencao_min": min(notas) if notas else None,
        "manutencao_max": max(notas) if notas else None,
        "manutencao_varia": len(set(notas)) > 1,
        "sem_acostamento_em_todas":
            len([l for l in linhas if l["acostamento"] is False]) == n,
        "sem_iluminacao_em_todas":
            len([l for l in linhas if l["iluminacao"] is False]) == n,
        "vias_sem_sinalizacao_turistica": len(sem_tur),
    }


# ══════════════════════════════════════════════════════════════════════════════
# CONJUNTO POR MUNICÍPIO
# ══════════════════════════════════════════════════════════════════════════════
def indicadores_de_campo(m, fichas: dict | None = None,
                         avaliacoes: dict | None = None,
                         coordenadas: dict | None = None,
                         rota_internacional: bool | None = None,
                         classes=None) -> dict:
    """Todos os indicadores de campo do município.

    Os insumos podem ser passados prontos; o que faltar é lido do acervo.
    """
    fichas = carregar_fichas(m) if fichas is None else fichas
    av = carregar_avaliacoes(m) if avaliacoes is None else avaliacoes
    if rota_internacional is None:
        rota_internacional = rota_aerea_internacional(m)

    aduanas = numeros_de(fichas, "Aduana")
    terminais = numeros_de(fichas, "Rodoviária", "Aeroporto", "Aduana")
    vias = numeros_de(fichas, "Geral")

    out = {
        "presencas_terminais": presencas_nos_pontos(fichas, pp.CHEGADA,
                                                    terminais),
        "presencas_via": presencas_nos_pontos(fichas, pp.INTERNA, vias),
        "presencas_aduana": (presencas_nos_pontos(fichas, pp.ADUANA, aduanas)
                             if aduanas else None),
        "rodoviaria": itens_do_terminal(fichas, "Rodoviária", pp.RODOVIARIA),
        "aeroporto": itens_do_terminal(fichas, "Aeroporto", pp.AEROPORTO),
        "avaliacao_chegada": notas_por_ponto(av, "chegada"),
        "avaliacao_interna": notas_por_ponto(av, "interna"),
    }
    vias_c = None
    if any((f.get("via") or {}) for f in fichas.values()):
        coords = (coordenadas_dos_pontos(m) if coordenadas is None
                  else coordenadas)
        vias_c = caracterizacao_das_vias(m, fichas, av, coords, classes)
    out["caracterizacao_via"] = vias_c
    out["resumo_caracterizacao_via"] = resumo_caracterizacao(vias_c)
    out["vias_de_chegada"] = vias_de_chegada(fichas, av)
    out["resumo_vias_de_chegada"] = resumo_vias_de_chegada(
        out["vias_de_chegada"])
    out["resumo_rodoviaria"] = resumo_rodoviaria(out["rodoviaria"])
    out["resumo_aeroporto"] = resumo_aeroporto(out["aeroporto"],
                                               rota_internacional)
    out["resumo_aduanas"] = resumo_aduanas(out["presencas_aduana"], av)
    out["ausentes_em_todos_terminais"] = ausentes_em_todos(
        out["presencas_terminais"])
    out["ausentes_em_todos_vias"] = ausentes_em_todos(out["presencas_via"])
    out["taxi_e_locadora"] = taxi_e_locadora_na_chegada(
        out["presencas_terminais"], out["aeroporto"], av)
    out["resumo_avaliacao_chegada"] = resumo_avaliacao_chegada(av)
    out["resumo_avaliacao_interna"] = resumo_avaliacao_interna(av)
    return out


# ══════════════════════════════════════════════════════════════════════════════
# TABELAS
# ══════════════════════════════════════════════════════════════════════════════
def _lista(xs) -> str:
    return "; ".join(str(x) for x in (xs or []))


def tabelas(indicadores: dict) -> dict:
    """{aba: DataFrame} a partir de {slug: indicadores_de_campo(m)}."""
    import pandas as pd

    t: dict[str, list] = {k: [] for k in (
        "presencas", "presencas_resumo", "terminais_itens",
        "rodoviaria_resumo", "aeroporto_resumo", "aduanas_resumo",
        "chegada_taxi_locadora", "notas_pontos", "notas_resumo",
        "vias_chegada", "vias_chegada_resumo", "vias_caracterizacao",
        "vias_caracterizacao_resumo")}
    for slug, ind in indicadores.items():
        m = POR_SLUG[slug]
        base = {"slug": slug, "municipio": m.nome, "uf": m.uf}
        for conj, chave in (("chegada", "presencas_terminais"),
                            ("vias", "presencas_via"),
                            ("aduana", "presencas_aduana")):
            b = ind.get(chave)
            if not b:
                continue
            todos = set(ausentes_em_todos(b))
            for l in b["linhas"]:
                for n, e in zip(b["pontos"], l["estados"]):
                    t["presencas"].append({**base, "conjunto": conj,
                                           "tema": l["tema"],
                                           "item": l["item"], "ponto": n,
                                           "estado": e,
                                           "ausente_em_todos":
                                               l["item"] in todos})
            t["presencas_resumo"].append({
                **base, "conjunto": conj, "pontos": _lista(b["pontos"]),
                "itens": b["itens"],
                "ausentes_em_todos": b["ausentes_em_todos"],
                "itens_ausentes_em_todos": _lista(ausentes_em_todos(b))})
        for terminal in ("rodoviaria", "aeroporto"):
            b = ind.get(terminal)
            for l in (b or {}).get("linhas", []):
                t["terminais_itens"].append({
                    **base, "terminal": terminal, "ponto": b["ponto"],
                    "tema": l["tema"], "item": l["item"],
                    "estado": l["estado"]})
        for aba, chave in (("rodoviaria_resumo", "resumo_rodoviaria"),
                           ("aeroporto_resumo", "resumo_aeroporto"),
                           ("aduanas_resumo", "resumo_aduanas"),
                           ("chegada_taxi_locadora", "taxi_e_locadora"),
                           ("vias_chegada_resumo", "resumo_vias_de_chegada"),
                           ("vias_caracterizacao_resumo",
                            "resumo_caracterizacao_via")):
            r = ind.get(chave)
            if r:
                t[aba].append({**base, **{k: (_lista(v) if isinstance(
                    v, (list, tuple, set)) else v) for k, v in r.items()}})
        for grupo in ("chegada", "interna"):
            b = ind.get(f"avaliacao_{grupo}")
            for x in (b or {}).get("notas", []):
                t["notas_pontos"].append({**base, "grupo": grupo, **x})
        rc, ri = ind["resumo_avaliacao_chegada"], ind["resumo_avaliacao_interna"]
        linha = {
            **base,
            "chegada_menores": _lista(k for k, _ in rc["menores"]),
            "chegada_menores_medias": _lista(v for _, v in rc["menores"]),
            "chegada_maiores": _lista(k for k, _ in rc["maiores"]),
            "chegada_maiores_medias": _lista(v for _, v in rc["maiores"]),
            "interna_pontos": ri["pontos"],
            "interna_media_via": ri["media_via"],
            "interna_media_calcada": ri["media_calcada"],
            "interna_vantagem": ri["vantagem"]}
        for i, (p, cs) in enumerate(ri["menores_avaliacoes"], 1):
            linha[f"interna_menor_ponto_{i}"] = p
            linha[f"interna_menor_elementos_{i}"] = _lista(cs)
        t["notas_resumo"].append(linha)
        for l in ind.get("vias_de_chegada") or []:
            t["vias_chegada"].append({**base, **l})
        for p in ind.get("caracterizacao_via") or []:
            linha = {**base, **{k: v for k, v in p.items()
                                if k != "tipos_de_fluxo"}}
            for tipo in fichas_p4.TIPOS_FLUXO:
                linha[f"fluxo_{tipo}"] = (p.get("tipos_de_fluxo")
                                          or {}).get(tipo)
            t["vias_caracterizacao"].append(linha)
    return {aba: pd.DataFrame(linhas) for aba, linhas in t.items()}


if __name__ == "__main__":
    import pandas as pd

    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    saida = DIR_DADOS
    if "--saida" in args:
        i = args.index("--saida")
        saida = Path(args[i + 1])
        del args[i:i + 2]
    alvos = [POR_SLUG[a] for a in args] or list(MUNICIPIOS)
    ind = {}
    for m in alvos:
        ind[m.slug] = indicadores_de_campo(m)
        print(f"   {m.nome_uf}")
    saida.mkdir(parents=True, exist_ok=True)
    arq = saida / "indicadores_campo.xlsx"
    with pd.ExcelWriter(arq, engine="openpyxl") as w:
        for aba, df in tabelas(ind).items():
            df.to_excel(w, sheet_name=aba, index=False)
    print(f"{len(ind)} municípios -> {arq}")
