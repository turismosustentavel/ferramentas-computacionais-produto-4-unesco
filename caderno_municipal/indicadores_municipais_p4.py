# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMAÇÕES POR MUNICÍPIO | PRODUTO 4
INDICADORES MUNICIPAIS DE ACESSO, MOBILIDADE E CONECTIVIDADE
================================================================================
Calcula, por município, os indicadores derivados das bases secundárias e da
modelagem (isócronas, malha rodoviária, contagem de tráfego, oferta de
ônibus, malha aérea, náutica, deslocamento interno e conectividade). Os
indicadores dos pontos aferidos em campo estão em `indicadores_campo_p4`.

INDICADORES (definição; fonte)
    Tempo por estrada (isócronas: intervalo [rápido, lento], em horas;
    OpenStreetMap, 2026)
        faixa_de_tempo            média do intervalo; valor único quando os
                                  extremos diferem menos de 0,02 h; faixa
                                  estreita quando a amplitude é de até 15% da
                                  média; média arredondada a 5 minutos.
        municipio_mais_proximo    município do estudo de menor tempo lento;
                                  contíguo abaixo de 5 minutos.
        alcance_rodoviario        municípios do estudo a até 2 h (tempo lento).
        tempo_ate_capital         capital do estado do município.
        cidades_em_frente         cidades do outro lado da linha
                                  (comum.FRONTEIRICAS).
        fronteiras_mais_proximas  as duas passagens de fronteira de menor tempo
                                  até a cidade estrangeira, com o município
                                  brasileiro de cada uma.
    Localização (metricas_situacao; IBGE, 2025)
        fronteira_internacional   país mais próximo e distância; na faixa de
                                  150 km ou fora; segundo país a até 50 km.
    Malha rodoviária e tráfego (DNIT, SNV/CIDE e PNCT)
        eixos_rodoviarios         rodovias federais com ao menos 0,1 km no
                                  município; rodovias de mesma extensão contam
                                  como um só eixo (traçado compartilhado);
                                  rodovias estaduais.
        trafego_de_acesso         participação dos veículos comerciais no
                                  trecho de maior movimento (corte em 30%);
                                  maior volume do recorte acima de 1,5 vez o
                                  do trecho; ferrovia no recorte sem alcançar
                                  o município.
        modos_de_chegada          presença de travessia de fronteira, de
                                  malha aérea regular e de uso náutico.
    Ônibus (ANTT, 2025; ClickBus, set. 2026; DER-PR)
        onibus_interestadual      as duas UF de maior participação nas
                                  passagens; ausência de linha regulada.
        ligacoes_onibus           oferta por destino (duração, partidas em dia
                                  útil e sábado, preço, operadoras, viagem só
                                  com baldeação); sem a coleta própria, a
                                  amostra do acervo.
        resumo_ligacoes_onibus    viagens diretas abaixo de 4 h e razão entre o
                                  tempo de ônibus e o de carro (carro de ao
                                  menos 10 minutos; razões abaixo de 0,95
                                  descartadas como medidas desencontradas);
                                  classe da razão (até 1,5; acima de 1,5;
                                  mista); destinos de longa distância com mais
                                  partidas.
        rede_entre_municipios     por município do estudo: situação da oferta,
                                  duração, tempo de carro e razão
                                  ônibus/carro; ligação mais rápida, ligações
                                  abaixo de 1 h, baldeação de maior razão,
                                  amplitude da razão nas diretas, oferta só em
                                  dia útil.
        baldeacoes                cidade em que ocorre a troca de ônibus e
                                  espera na conexão.
    Malha aérea (ANAC, 2025)
        rede_aerea                rota dominante (ao menos 90% dos
                                  passageiros) e rotas residuais (menos de 1%
                                  e menos de mil passageiros); duração do
                                  ônibus para o mesmo destino (4 h ou mais).
    Náutica e fronteira (ANTAQ; OpenStreetMap)
        infraestrutura_nautica, travessias
    Deslocamento interno (Receita Federal, CNPJ das ACTs; TomTom Routing)
        distancia_dos_atrativos   distância pela rota modelada ou, sem ela, em
                                  linha reta; tempo a 30 km/h.
        deslocamento_interno      concentração das ACTs a 5 km, trajeto médio
                                  e linha reta, sobreposição dos trajetos.
    Conectividade (ANATEL, 2025; listas oficiais das plataformas)
        resumo_conectividade      indicadores em que lidera, em que fica
                                  abaixo da metade (posição acima de 6),
                                  plataformas nacionais e aplicativos locais.
    Posição entre os doze (IBGE, RAIS, CADASTUR)
        posicao_regional          indicadores agrupados por posição.

ENTRADAS (relativas a P4_DADOS)
    Entregas/Produto 4/produção/Caderno de informações por município/
        02_Dados_Municipais/isocronas/<slug>/metricas_isocronas_<slug>.json
            (23_isocronas_municipio.py)
        02_Dados_Municipais/<slug>/metricas_contexto_<slug>.json
            rodovias, tráfego, ônibus (ANTT e amostra ClickBus), aéreo,
            náutica (contexto_p4.py)
        02_Dados_Municipais/<slug>/metricas_deslocamento_<slug>.json
            ACTs, atrativos, trajetos e sobreposição
            (deslocamento_interno_p4.py)
        02_Dados_Municipais/<slug>/metricas_situacao_<slug>.json
            capital, distâncias à linha internacional e aos países vizinhos
            (localizacao_p4.py)
        02_Dados_Municipais/<slug>/metricas_matrizes_<slug>.json
            postos de fronteira aferidos (avaliacao_pontos_p4.py, lido por
            indicadores_campo_p4)
        02_Dados_Municipais/<slug>/perfil_municipal.json
            (12_montar_perfil_municipal.py)
        02_Dados_Municipais/<slug>/metricas_perfil_<slug>.json
            posição entre os doze (indicadores_perfil_p4.py)
        02_Dados_Municipais/oferta_clickbus/oferta_clickbus_<slug>.json
            oferta por destino, em dia útil e sábado ("datas", "grupos",
            "por_data")
        02_Dados_Municipais/oferta_clickbus/rede_do_estudo_<slug>.json
            oferta até os demais municípios do estudo, com linha do DER-PR
        02_Dados_Municipais/oferta_clickbus/pernas_<slug>.json
            caminho das viagens com baldeação
    Módulos do repositório: conectividade_p4 (indicadores da ANATEL e
    posição), indicadores_campo_p4 (médias de avaliação e postos de
    fronteira), comum (FRONTEIRICAS).

ORDEM
    Depois de 23_isocronas_municipio.py, indicadores_perfil_p4.py,
    localizacao_p4.py, deslocamento_interno_p4.py, contexto_p4.py e
    avaliacao_pontos_p4.py.

SAÍDAS
    02_Dados_Municipais/indicadores_municipais.xlsx, uma aba por tema.

COMO EXECUTAR
    python indicadores_municipais_p4.py                 os doze municípios
    python indicadores_municipais_p4.py 07_Mundo_Novo_MS
    python indicadores_municipais_p4.py --saida <pasta> grava em outra pasta
================================================================================
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import conectividade_p4 as cn                                    # noqa: E402
import indicadores_campo_p4 as ic                                # noqa: E402
from comum import (DIR_DADOS, FRONTEIRICAS, MUNICIPIOS,          # noqa: E402
                   POR_SLUG, fronteiricas_de)

OFERTA = DIR_DADOS / "oferta_clickbus"


# ══════════════════════════════════════════════════════════════════════════════
# LEITURA
# ══════════════════════════════════════════════════════════════════════════════
def _json(p: Path) -> dict:
    return json.loads(p.read_text("utf-8")) if p.exists() else {}


def _do_municipio(m, nome: str) -> Path:
    return DIR_DADOS / m.slug / f"{nome}_{m.slug}.json"


def arquivo_isocronas(m) -> Path:
    return DIR_DADOS / "isocronas" / m.slug / f"metricas_isocronas_{m.slug}.json"


def arquivo_posicao(m) -> Path:
    return _do_municipio(m, "metricas_perfil")


def arquivo_oferta(m) -> Path:
    return OFERTA / f"oferta_clickbus_{m.slug}.json"


def arquivo_rede(m) -> Path:
    return OFERTA / f"rede_do_estudo_{m.slug}.json"


def arquivo_baldeacoes(m) -> Path:
    return OFERTA / f"pernas_{m.slug}.json"


def isocronas(m) -> dict:
    return _json(arquivo_isocronas(m))


def contexto(m) -> dict:
    return _json(_do_municipio(m, "metricas_contexto"))


def deslocamento(m) -> dict:
    return _json(_do_municipio(m, "metricas_deslocamento"))


def situacao(m) -> dict:
    return _json(_do_municipio(m, "metricas_situacao"))


def perfil(m) -> dict:
    return _json(m.dir_dados / "perfil_municipal.json")


def posicoes_do_municipio(m) -> dict:
    """{indicador: {"posicao", ...}} entre os doze municípios."""
    return _json(arquivo_posicao(m)).get("posicao_regional") or {}


# ══════════════════════════════════════════════════════════════════════════════
# DURAÇÕES E TEMPOS
# ══════════════════════════════════════════════════════════════════════════════
def horas_de_duracao(txt) -> float | None:
    """'16h 30m' -> 16.5; '1d 6h 0m' -> 30.0; sem número -> None."""
    s = str(txt or "")
    d = re.search(r"(\d+)\s*d", s)
    h = re.search(r"(\d+)\s*h", s)
    mi = re.search(r"(\d+)\s*m", s)
    if not (d or h or mi):
        return None
    return ((int(d.group(1)) * 24 if d else 0)
            + (int(h.group(1)) if h else 0)
            + (int(mi.group(1)) / 60 if mi else 0))


def horas_de_duracao_hm(r: dict) -> float:
    """Horas de uma ligação cuja duração está na forma 'Xh Ym'.

    Fora dessa forma (com dia, ou só minutos), devolve 99.
    """
    t = str(r.get("duracao", "")).lower().replace(" ", "")
    h, _, m = t.partition("h")
    try:
        return int(h) + int((m.replace("m", "") or 0)) / 60
    except ValueError:
        return 99


def tempo_lento(v):
    """Limite superior do intervalo [rápido, lento]."""
    return v[1] if isinstance(v, (list, tuple)) else v


def faixa_de_tempo(v) -> dict:
    """Componentes numéricos de um tempo de percurso por estrada.

    `v` é o intervalo [rápido, lento] em horas, ou um valor único.
    """
    if isinstance(v, (list, tuple)):
        a, b = v
        unico = abs(a - b) < 0.02
    else:
        a = b = v
        unico = True
    med = (a + b) / 2
    return {"rapido_h": a, "lento_h": b, "medio_h": med,
            "valor_unico": unico,
            "faixa_estreita": b - a <= 0.15 * med,
            "medio_min_arred_5": int(5 * round(med * 60 / 5)),
            "rapido_min": int(round(a * 60)),
            "lento_min": int(round(b * 60))}


# Abaixo deste tempo de carro (h) entre centros, as áreas urbanas são
# contíguas.
CONTIGUO_H = 5 / 60
# Viagem de ida e volta no mesmo dia (h, tempo lento).
ALCANCE_H = 2


def municipio_mais_proximo(iso: dict) -> dict | None:
    """O município do estudo de menor tempo lento por estrada."""
    te = iso.get("tempo_h_municipios_estudo", {})
    viz = sorted(((k, tempo_lento(v)) for k, v in te.items()
                  if v is not None), key=lambda x: x[1])
    if not viz:
        return None
    k = viz[0][0]
    return {"municipio": k, **faixa_de_tempo(te[k]),
            "contiguo": viz[0][1] < CONTIGUO_H}


def alcance_rodoviario(iso: dict) -> list[str]:
    """Municípios do estudo a até duas horas (tempo lento)."""
    te = {k: v for k, v in iso.get("tempo_h_municipios_estudo", {}).items()
          if v is not None}
    return [k for k, v in te.items() if tempo_lento(v) <= ALCANCE_H]


def tempo_ate_capital(m, iso: dict, sit: dict) -> dict | None:
    """Tempo por estrada até a capital do estado (se não for o município)."""
    ti = {k: v for k, v in iso.get("tempo_h_ate", {}).items()
          if v is not None}
    cap = sit.get("capital")
    if cap in ti and cap != m.nome:
        return {"capital": cap, **faixa_de_tempo(ti[cap])}
    return None


def cidades_em_frente(m, iso: dict) -> list[dict]:
    """As cidades do outro lado da linha, com o tempo por estrada."""
    tf = iso.get("tempo_h_cidades_fronteiricas", {})
    return [{"cidade": n, **faixa_de_tempo(tf[n])}
            for n, _, _ in fronteiricas_de(m.nome) if tf.get(n) is not None]


def fronteiras_mais_proximas(iso: dict, quantas: int = 2) -> list[dict]:
    """As passagens de fronteira mais próximas, pelo lado brasileiro.

    Ordena as cidades estrangeiras pelo tempo lento até elas e fica com as
    primeiras cujo município brasileiro em frente tem tempo calculado, sem
    repetir município. O tempo informado é o de carro até o município
    brasileiro.
    """
    te = iso.get("tempo_h_municipios_estudo") or {}
    tfr = iso.get("tempo_h_cidades_fronteiricas") or {}
    pares = []
    for n, _, _, gem in sorted(
            FRONTEIRICAS, key=lambda r: ((tfr.get(r[0]) or [99, 99])[-1])):
        br = next((g for g in gem if te.get(g)), None)
        if br and br not in [x[0] for x in pares]:
            pares.append((br, n))
        if len(pares) == quantas:
            break
    return [{"municipio": br, "cidade_estrangeira": n, **faixa_de_tempo(te[br])}
            for br, n in pares]


# ══════════════════════════════════════════════════════════════════════════════
# LOCALIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
FAIXA_KM = 150          # largura da faixa de fronteira
SEGUNDO_PAIS_KM = 50    # o segundo país só conta se estiver a até esta distância


def fronteira_internacional(perf: dict, sit: dict) -> dict:
    """Divisa internacional do município, ou a mais próxima dele."""
    idf = perf.get("identificacao", {})
    if idf.get("linha_internacional"):
        return {"faz_divisa": True,
                "paises_vizinhos": [p.strip() for p in re.split(
                    r",| e ", idf.get("pais_vizinho") or "") if p.strip()]}
    out = {"faz_divisa": False}
    if sit.get("distancia_paises_km"):
        dp = sorted(sit["distancia_paises_km"].items(), key=lambda kv: kv[1])
        p0, d0 = dp[0]
        out.update(pais_mais_proximo=p0, distancia_pais_km=d0,
                   na_faixa_de_fronteira=d0 <= FAIXA_KM)
        if len(dp) > 1 and dp[1][1] <= SEGUNDO_PAIS_KM:
            out.update(segundo_pais=dp[1][0],
                       distancia_segundo_pais_km=dp[1][1])
    elif sit.get("distancia_linha_internacional_km"):
        out["distancia_linha_internacional_km"] = \
            sit["distancia_linha_internacional_km"]
    return out


# ══════════════════════════════════════════════════════════════════════════════
# MALHA RODOVIÁRIA, TRÁFEGO E MODOS DE CHEGADA
# ══════════════════════════════════════════════════════════════════════════════
def eixos_rodoviarios(ctx: dict) -> dict | None:
    """Eixos federais e rodovias estaduais no território municipal.

    Rodovias federais com a mesma extensão no município correm no mesmo leito
    e contam como um eixo. Extensões abaixo de 0,1 km (rodovia que só
    encosta no limite) ficam fora.
    """
    ro = ctx.get("rodovias", {})
    if not ro:
        return None
    fed = {b: v["km_no_municipio"] for b, v in ro["federais"].items()
           if (v.get("km_no_municipio") or 0) >= 0.1}
    tracados: dict = {}
    for b, km in fed.items():
        tracados.setdefault(km, []).append(b)
    est = [e for e in ro.get("estaduais") or [] if not e.endswith("-nan")]
    return {"eixos_federais": [{"rodovias": bs, "km": km}
                               for km, bs in tracados.items()],
            "estaduais": est,
            "estaduais_km": ro.get("estaduais_km"),
            "pontes": len(ro.get("pontes", []))}


# Participação dos veículos comerciais a partir da qual o corredor é lido
# como de uso misto (turismo e carga), em %.
COMERCIAIS_PCT = 30
# Razão entre o maior volume do recorte e o do trecho no município.
RAZAO_VOLUME = 1.5


def trafego_de_acesso(ctx: dict) -> dict:
    """Trecho de maior movimento no município e ferrovia no recorte."""
    trf = ctx.get("trafego") or {}
    tr0 = (trf.get("trechos_no_municipio") or [None])[0]
    out = {"ferrovia_alcanca_o_municipio":
               bool(trf.get("ferrovia_alcanca_o_municipio")),
           "ferrovia_no_recorte_sem_alcance":
               bool(trf.get("ferrovia_linhas_no_recorte")
                    and not trf.get("ferrovia_alcanca_o_municipio")),
           "linhas_ferreas_no_recorte":
               trf.get("ferrovia_linhas_no_recorte") or []}
    if tr0 and tr0.get("veiculos_dia"):
        pct = round(100 * tr0["comerciais_dia"] / tr0["veiculos_dia"])
        out.update(
            br=tr0["br"], veiculos_dia=tr0["veiculos_dia"],
            comerciais_dia=tr0["comerciais_dia"], pct_comerciais=pct,
            comerciais_acima_do_corte=pct >= COMERCIAIS_PCT,
            maior_volume_no_recorte=trf.get("maior_volume_no_recorte"),
            recorte_acima_da_razao=(trf.get("maior_volume_no_recorte", 0)
                                    > tr0["veiculos_dia"] * RAZAO_VOLUME))
    return out


def modos_de_chegada(m, ctx: dict, avaliacoes: dict) -> dict:
    """Modos presentes na chegada ao município."""
    ro = ctx.get("rodovias", {})
    ha_aduana = any("Aduana" in str(g.get("formulario", ""))
                    for g in avaliacoes.get("grade", []))
    na = ctx.get("nautica") or {}
    return {
        "travessia_de_fronteira": bool(ro.get("pontes") or ha_aduana),
        "aereo_regular": bool((ctx.get("aereo") or {}).get("rotas")),
        "nautico": bool(m.agua_navegavel and (
            na.get("pontos_nomeados_no_municipio") or na.get("portos_antaq")
            or na.get("travessias") or na.get("hidrovias"))),
        "ferrovia_de_carga_no_territorio":
            bool((ctx.get("trafego") or {}).get("ferrovia_alcanca_o_municipio")),
    }


def infraestrutura_nautica(m, ctx: dict) -> dict:
    na = ctx.get("nautica") or {}
    return {"uso_nautico": modos_de_chegada(m, ctx, {})["nautico"],
            "hidrovias": na.get("hidrovias") or [],
            "portos_antaq": len(na.get("portos_antaq") or []),
            "travessias": len(na.get("travessias") or []),
            "pontos_nomeados": len(na.get("pontos_nomeados_no_municipio")
                                   or [])}


# Onde o fim da rodovia na fronteira não é ponte (OpenStreetMap, conferido
# em 05/10/2026): o rótulo genérico "Ponte internacional" não conta.
TRAVESSIA_SEM_PONTE = {"07_Mundo_Novo_MS": "fronteira seca",
                       "08_Ponta_Pora_MS": "fronteira seca",
                       "09_Porto_Murtinho_MS": "travessia fluvial"}


def travessias(m, ctx: dict, avaliacoes: dict) -> dict:
    """Pontes internacionais e postos de fronteira aferidos."""
    pontes = (ctx.get("rodovias") or {}).get("pontes") or []
    if m.slug in TRAVESSIA_SEM_PONTE:
        pontes = [p for p in pontes if p.lower() != "ponte internacional"]
    aduanas = [g for g in avaliacoes.get("grade", [])
               if "Aduana" in str(g.get("formulario", ""))]
    return {"pontes": len(pontes),
            "pontes_nomeadas": [p for p in pontes
                                if p.lower() != "ponte internacional"],
            "sem_ponte": TRAVESSIA_SEM_PONTE.get(m.slug),
            "postos_de_fronteira": [a["numero"] for a in aduanas]}


# ══════════════════════════════════════════════════════════════════════════════
# ÔNIBUS
# ══════════════════════════════════════════════════════════════════════════════
def onibus_interestadual(ctx: dict) -> dict | None:
    """Bilhetagem interestadual (ANTT): as duas UF de maior participação."""
    on = ctx.get("onibus", {})
    if not on:
        return None
    if not on.get("passagens_total"):
        return {"sem_linha_regulada": True}
    ufs = list(on.get("pct_por_uf", {}).items())[:2]
    out = {"sem_linha_regulada": False,
           "passagens_total": on["passagens_total"],
           "ligacoes": on.get("ligacoes"), "top10_pct": on.get("top10_pct")}
    for i, (uf, pct) in enumerate(ufs, 1):
        out[f"uf_{i}"], out[f"pct_uf_{i}"] = uf, pct
    return out


def chave(s) -> str:
    t = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in t if not unicodedata.combining(c)).lower().strip()


# A consulta à oferta vai sem acento; os nomes do estudo vêm de `comum` e os
# demais desta lista.
_ACENTO = {"guaira": "Guaíra", "maringa": "Maringá",
           "paranavai": "Paranavaí", "florianopolis": "Florianópolis",
           "sao paulo": "São Paulo", "dionisio cerqueira": "Dionísio Cerqueira",
           "marechal candido rondon": "Marechal Cândido Rondon",
           "barracao": "Barracão", "assis chateaubriand": "Assis Chateaubriand",
           "ponta grossa": "Ponta Grossa"}


def com_acento(nome: str) -> str:
    por_slug = {chave(m.nome): m.nome for m in POR_SLUG.values()}
    c = chave(nome)
    return por_slug.get(c) or _ACENTO.get(c, nome)


def ligacoes_do_levantamento(m) -> list[dict]:
    """Oferta consultada na plataforma, em dia útil (primeira data) e sábado
    (última data). O destino é a cidade e a UF, sem caixa nem acento: a
    mesma cidade em duas grafias conta uma vez. Consulta que falhou ou sem
    duração fica fora."""
    arq = arquivo_oferta(m)
    if not arq.exists():
        return []
    bruto = json.loads(arq.read_text("utf-8"))
    dias = bruto.get("datas") or []
    grupos = bruto.get("grupos") or {"": bruto.get("ligacoes") or []}
    estudo = {chave(x.nome) for x in POR_SLUG.values()}
    saida = []
    vistos = set()
    for grupo, ligacoes in grupos.items():
        for lg in ligacoes:
            destino = (chave(lg["cidade"]), lg["uf"])
            por_dia = lg.get("por_data") or {}
            util = por_dia.get(dias[0], {}) if dias else {}
            sab = por_dia.get(dias[-1], {}) if len(dias) > 1 else {}
            if (destino in vistos or util.get("falhou")
                    or not util.get("duracao_min")):
                continue
            vistos.add(destino)
            saida.append({
                "cidade": com_acento(lg["cidade"]), "uf": lg["uf"],
                "duracao": util["duracao_min"],
                "partidas_dia": util.get("partidas_dia"),
                "partidas_sabado": sab.get("partidas_dia"),
                "preco": util.get("preco_min"),
                "operadoras": ", ".join(util.get("viacoes") or []),
                "so_conexao": bool(util.get("somente_com_conexao")),
                "do_caderno": chave(lg["cidade"]) in estudo,
                "grupo": grupo})
    return sorted(saida, key=lambda d: horas_de_duracao(d["duracao"]))


def ligacoes_da_amostra(ctx: dict) -> list[dict]:
    """Amostra de rotas do acervo (chegadas e linhas), com duração válida."""
    cb = ctx.get("onibus_clickbus", {})
    por: dict[str, dict] = {}
    for r in cb.get("chegadas", []):
        por[r["cidade"]] = {**r, "preco": r.get("preco_medio"),
                            "operadoras": r.get("viacoes")}
    for r in cb.get("linhas", []):
        base = por.get(r["cidade"], {})
        por[r["cidade"]] = {**base, **r, "preco": r.get("preco_total"),
                            "operadoras": r.get("viacao")}
    return [d for d in por.values() if horas_de_duracao(d.get("duracao"))]


CAMPOS_LIGACAO = ("cidade", "uf", "partidas_dia", "partidas_sabado",
                  "duracao", "distancia_km", "preco", "operadoras",
                  "so_conexao")


def ligacoes_onibus(m, ctx: dict | None = None) -> list[dict] | None:
    """Uma linha por destino, ordenada pela duração da viagem.

    A coleta própria substitui a amostra do acervo onde existe.
    `destino_do_estudo` só é conhecido na coleta própria.
    """
    lev = ligacoes_do_levantamento(m)
    dados = lev or ligacoes_da_amostra(contexto(m) if ctx is None else ctx)
    if not dados:
        return None
    dados.sort(key=lambda d: horas_de_duracao(d["duracao"]))
    fonte = "oferta consultada" if lev else "amostra do acervo"
    return [{**{k: d.get(k) for k in CAMPOS_LIGACAO},
             "destino_do_estudo": d.get("do_caderno"), "fonte": fonte}
            for d in dados]


# Duração (h) abaixo da qual a viagem é curta; tempo mínimo de carro (h) para
# comparar os modos; razão abaixo da qual o par é descartado.
CURTA_H = 4
CARRO_MIN_H = 10 / 60
RAZAO_MIN = 0.95
RAZAO_CORTE = 1.5


def resumo_ligacoes_onibus(m, ligacoes: list | None, iso: dict) -> dict:
    """Viagens curtas, razão ônibus/carro e frequência das longas."""
    lig = ligacoes or []
    dire = [r for r in lig if not r.get("so_conexao")]
    curtas = [r for r in dire if horas_de_duracao_hm(r) < CURTA_H]
    longas = sorted([r for r in dire if CURTA_H <= horas_de_duracao_hm(r) < 99
                     and r.get("partidas_dia")],
                    key=lambda r: -r["partidas_dia"])
    out = {"ligacoes": len(lig), "diretas": len(dire),
           "curtas": [r["cidade"] for r in curtas],
           "curtas_no_estado": None, "razoes": [], "razoes_descartadas": [],
           "razao_min": None, "razao_max": None, "classe_razao": None,
           "cidade_razao_min": None, "razao_em_todas_as_curtas": None,
           "longas": [(r["cidade"], r["partidas_dia"]) for r in longas],
           "empate_nas_longas": None, "cauda": None}
    if curtas:
        out["curtas_no_estado"] = all(r["uf"] == m.uf for r in curtas)
        carro = {**(iso.get("tempo_h_ate") or {}),
                 **(iso.get("tempo_h_municipios_estudo") or {})}
        raz = []
        for r in curtas[:3]:
            c = carro.get(r["cidade"])
            if c:
                c = (c[0] + c[1]) / 2 if isinstance(c, (list, tuple)) else c
                if c >= CARRO_MIN_H:
                    raz.append((horas_de_duracao_hm(r) / c, r["cidade"]))
        out["razoes_descartadas"] = [(c, x) for x, c in raz if x < RAZAO_MIN]
        raz = [x for x in raz if x[0] >= RAZAO_MIN]
        out["razoes"] = [(c, x) for x, c in raz]
        if raz:
            lo, hi = min(raz)[0], max(raz)[0]
            out.update(
                razao_min=lo, razao_max=hi,
                classe_razao=("até 1,5" if hi <= RAZAO_CORTE else
                              "acima de 1,5" if lo > RAZAO_CORTE else "mista"),
                cidade_razao_min=min(raz)[1],
                razao_em_todas_as_curtas=len(raz) == len(curtas[:3]))
    if len(longas) >= 2:
        a, b = longas[:2]
        z = longas[-1]
        out["empate_nas_longas"] = a["partidas_dia"] == b["partidas_dia"]
        if len(longas) > 2 and z["partidas_dia"] < b["partidas_dia"]:
            out["cauda"] = (z["cidade"], z["partidas_dia"])
    return out


def rede_entre_municipios(m, iso: dict | None = None) -> dict | None:
    """Oferta de ônibus até os demais municípios do estudo, na ordem do
    arquivo, com o tempo de carro das isócronas e a razão ônibus/carro.

    A razão só existe com carro de ao menos 10 minutos (entre cidades
    contíguas o carro não serve de régua).
    """
    bruto = _json(arquivo_rede(m))
    dados = bruto.get("municipios") or []
    if not dados:
        return None
    iso = isocronas(m) if iso is None else iso
    te = iso.get("tempo_h_municipios_estudo") or {}
    linhas = []
    for d in dados:
        d = dict(d)
        if d.get("municipio") in te:
            d["carro_h"] = te[d["municipio"]]
        c = d.get("carro_h")
        medio = (c[0] + c[1]) / 2 if c else None
        comparavel = medio if medio and medio >= CARRO_MIN_H else None
        h = horas_de_duracao(d.get("duracao"))
        linhas.append({
            "municipio": d.get("municipio"), "uf": d.get("uf"),
            "estado": d.get("estado"), "duracao": d.get("duracao"),
            "horas": h, "carro_h": c, "carro_medio_h": medio,
            "carro_comparavel": comparavel is not None,
            "razao_onibus_carro": (h / comparavel if (comparavel and h)
                                   else None),
            "partidas_util": d.get("partidas_util"),
            "partidas_sabado": d.get("partidas_sabado"),
            "preco_min": d.get("preco_min"), "viacoes": d.get("viacoes"),
            "tarifa_der": d.get("tarifa_der"), "linha_der": d.get("linha_der"),
            "empresa_der": d.get("empresa_der"),
            "sem_oferta_no_sabado": bool(d.get("partidas_util")
                                         and not d.get("partidas_sabado"))})
    return {"datas": bruto.get("datas"), "municipios": linhas}


def resumo_rede(m, rede: dict | None) -> dict | None:
    """Síntese da oferta entre os municípios do estudo."""
    if not rede:
        return None
    mm = rede["municipios"]

    def _h(x):
        return x["horas"] or 99

    def _r(x):
        return x["razao_onibus_carro"]

    por = {x["estado"]: [y for y in mm if y["estado"] == x["estado"]]
           for x in mm}
    diretas = por.get("direta") or []
    conexao = por.get("só com conexão") or []
    rapidas = sorted(diretas, key=_h)
    perto = [x for x in rapidas if _h(x) < 1]
    melhor = rapidas[0] if rapidas else None
    consultados = {x["municipio"] for x in mm}
    fora_consulta = [x.nome for x in POR_SLUG.values()
                     if x.nome != m.nome and x.nome not in consultados]
    uf_de = {x.nome: x.uf for x in POR_SLUG.values()}
    fora = [x for x in mm if x["estado"] == "fora da plataforma"]
    nada = [x for x in mm if x["estado"] == "nenhuma oferta"]
    out = {
        "municipios_analisados": len(mm) + len(fora_consulta),
        "fora_da_consulta": fora_consulta,
        "por_estado": {k: len(v) for k, v in por.items()},
        "mais_rapida": melhor["municipio"] if melhor else None,
        "mais_rapida_h": melhor["horas"] if melhor else None,
        "mais_rapida_partidas_util": melhor["partidas_util"] if melhor else None,
        "abaixo_de_1h": [x["municipio"] for x in perto],
        "demais_diretas": None, "demais_direta_mais_curta": None,
        "demais_direta_mais_curta_h": None, "demais_so_com_conexao": None,
        "demais_fora_da_plataforma": None, "demais_sem_oferta": None,
        "fora_da_plataforma": [(x["municipio"], x["tarifa_der"])
                               for x in fora],
        "linha_der": fora[0]["linha_der"] if fora else None,
        "empresa_der": fora[0]["empresa_der"] if fora else None,
        "sem_oferta": [x["municipio"] for x in nada],
        "sem_oferta_e_sem_linha_der_pr": (
            m.uf == "PR" and all(uf_de.get(x["municipio"]) == "PR"
                                 for x in nada)) if nada else None,
        "sem_oferta_no_sabado": [x["municipio"] for x in mm
                                 if x["sem_oferta_no_sabado"]],
        "baldeacao_maior_razao": None, "baldeacao_maior_razao_valor": None,
        "diretas_razao_min": None, "diretas_razao_max": None,
        "baldeacao_supera_diretas": None,
    }
    if melhor:
        ja = perto or [melhor]
        outros = [x for x in mm if x not in ja]
        od = [x for x in outros if x["estado"] == "direta"]
        out.update(
            demais_diretas=len(od),
            demais_so_com_conexao=len([x for x in outros
                                       if x["estado"] == "só com conexão"]),
            demais_fora_da_plataforma=len(
                [x for x in outros if x["estado"] == "fora da plataforma"]),
            demais_sem_oferta=len([x for x in outros
                                   if x["estado"] == "nenhuma oferta"]))
        if od:
            mc_ = min(od, key=_h)
            out.update(demais_direta_mais_curta=mc_["municipio"],
                       demais_direta_mais_curta_h=mc_["horas"])
    # razão das ligações diretas, sem as medidas desencontradas (< 0,95)
    dr = sorted([x for x in diretas if (_r(x) or 0) >= RAZAO_MIN], key=_r)
    if dr:
        out["diretas_razao_min"] = (dr[0]["municipio"], _r(dr[0]))
        out["diretas_razao_max"] = (dr[-1]["municipio"], _r(dr[-1]))
    pior = max((x for x in conexao if _r(x)), key=_r, default=None)
    if pior:
        out.update(baldeacao_maior_razao=pior["municipio"],
                   baldeacao_maior_razao_valor=_r(pior),
                   baldeacao_supera_diretas=(not dr
                                             or _r(pior) > _r(dr[-1])))
    return out


def baldeacoes(m) -> dict | None:
    """Cidades em que ocorre a troca de ônibus e a espera na conexão."""
    lg = _json(arquivo_baldeacoes(m)).get("ligacoes") or []
    if not lg:
        return None
    troca: dict = {}
    for x in lg:
        cam = [c[0] if isinstance(c, (list, tuple)) else c
               for c in (x.get("caminho") or [])]
        if x.get("tipo") == "conexão" and len(cam) > 2:
            troca.setdefault(cam[1], []).append(x["destino"])
    maior = max(troca.items(), key=lambda kv: len(kv[1]), default=None)
    espera = {x["destino"]: x.get("espera") for x in lg if x.get("espera")}
    out = {"cidades_de_troca": troca,
           "cidade_principal": maior[0] if maior else None,
           "espera_destino": None, "espera": None, "espera_h": None}
    if espera:
        n, e = next(iter(espera.items()))
        out.update(espera_destino=n, espera=e,
                   espera_h=horas_de_duracao(e.split(" em ")[0]))
    return out


# ══════════════════════════════════════════════════════════════════════════════
# MALHA AÉREA
# ══════════════════════════════════════════════════════════════════════════════
DOMINANTE_PCT = 90
RESIDUAL_PCT, RESIDUAL_PASSAGEIROS = 1, 1000


def rede_aerea(ctx: dict, ligacoes: list | None) -> dict | None:
    """Rotas regulares, concentração e comparação com o ônibus."""
    ae = ctx.get("aereo", {})
    if not ae:
        return None
    pr_all = ae.get("principais") or []
    resid = [x for x in pr_all[1:]
             if x["pct"] < RESIDUAL_PCT and x["passageiros"] < RESIDUAL_PASSAGEIROS]
    dom = (pr_all[0] if resid and pr_all and pr_all[0]["pct"] >= DOMINANTE_PCT
           else None)
    pr_ae = (ae.get("principais") or [None])[0]
    bus = None
    if pr_ae:
        base = pr_ae["cidade"].split("/")[0]
        bus = next((r for r in (ligacoes or []) if r["cidade"] == base), None)
    return {
        "rotas": ae.get("rotas"),
        "internacionais": [x["cidade"] for x in
                           ((ae or {}).get("internacionais") or [])],
        "passageiros": ae.get("passageiros"),
        "rotas_sem_fluxo": ae.get("rotas_sem_fluxo") or [],
        "rota_principal": pr_ae["cidade"] if pr_ae else None,
        "pct_rota_principal": pr_ae["pct"] if pr_ae else None,
        "rota_dominante": dom["cidade"] if dom else None,
        "rotas_residuais": [x["cidade"] for x in resid],
        "residuais_entre_50_e_150": (all(50 <= x["passageiros"] <= 150
                                         for x in resid) if resid else None),
        "onibus_mesmo_destino_h": (horas_de_duracao_hm(bus)
                                   if bus and horas_de_duracao_hm(bus) >= CURTA_H
                                   else None),
    }


# ══════════════════════════════════════════════════════════════════════════════
# DESLOCAMENTO INTERNO
# ══════════════════════════════════════════════════════════════════════════════
VELOCIDADE_URBANA_KMH = 30


def distancia_dos_atrativos(desl: dict) -> list[dict] | None:
    """Atrativos de maior relevância pela distância ao centro da oferta.

    Pela rota modelada onde ela existe; em linha reta, e sem tempo, onde não
    existe. Tempo a 30 km/h, sem estacionamento nem espera.
    """
    princ = desl.get("atrativos", {}).get("principais") or []
    if not princ:
        return None
    dist = {p["nome"]: (p.get("rota_km") or p["distancia_km"]) for p in princ}
    reta = {p["nome"] for p in princ if not p.get("rota_km")}
    dados = sorted(dist.items(), key=lambda kv: kv[1])
    return [{"atrativo": n, "distancia_km": d, "em_linha_reta": n in reta,
             "minutos": (None if n in reta else
                         int(round(d / VELOCIDADE_URBANA_KMH * 60)))}
            for n, d in dados]


def deslocamento_interno(desl: dict) -> dict | None:
    """Concentração da oferta, dispersão dos atrativos e trajetos."""
    acts, atr = desl.get("acts", {}), desl.get("atrativos", {})
    traj, sob = desl.get("trajetos", {}), desl.get("sobreposicao", {})
    if not (acts or atr or traj or sob):
        return None
    return {
        "acts": acts.get("total"),
        "acts_envoltoria_km2": acts.get("envoltoria_km2"),
        "acts_ate_5km_pct": acts.get("dentro_de_5km_pct"),
        "acts_todas_ate_5km":
            round(acts.get("dentro_de_5km_pct") or 0, 1) >= 100,
        "acts_nenhuma_ate_5km": not acts.get("dentro_de_5km_pct"),
        "atrativos": atr.get("total"),
        "atrativos_distancia_media_km": atr.get("distancia_media_km"),
        "atrativos_distancia_max_km": atr.get("distancia_max_km"),
        "trajetos": traj.get("total"),
        "trajetos_extensao_somada_km": traj.get("extensao_somada_km"),
        "trajetos_extensao_media_km": traj.get("extensao_media_km"),
        "trajeto_medio_maior_que_linha_reta":
            ((atr.get("distancia_media_km") or 99)
             < (traj.get("extensao_media_km") or 0)),
        "rotas_no_agrupamento_mais_frequente": sob.get("rotas_no_maior_freq"),
        "todos_os_trajetos_no_mais_frequente":
            sob.get("rotas_no_maior_freq") == traj.get("total"),
        "agrupamentos_acima_da_media": sob.get("acima_da_media"),
        "agrupamentos": sob.get("total") or 100,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CONECTIVIDADE E POSIÇÃO
# ══════════════════════════════════════════════════════════════════════════════
# Posição acima da qual o município fica na metade inferior dos doze.
METADE = 6


def resumo_conectividade(m, cx: dict | None = None) -> dict | None:
    """Onde o município lidera, onde fica abaixo da metade, plataformas."""
    cx = cn.do_municipio(m.slug) if cx is None else cx
    if not cx or not cx["indicadores"]:
        return None
    ind = cx["indicadores"]
    pl = cx.get("plataformas") or {}
    loc = (cx.get("locais") or {}).get("mobilidade local", "")
    i0 = ind[0]
    return {
        "municipios": cx.get("n_municipios"),
        "lidera": [i["rotulo"] for i in ind
                   if i["maior_e_melhor"] and i["posicao"] == 1],
        "abaixo_da_metade": [i["rotulo"] for i in ind
                             if i["maior_e_melhor"] and i["posicao"] > METADE],
        "primeiro_indicador": i0["rotulo"],
        "primeiro_posicao": i0["posicao"], "primeiro_valor": i0["valor"],
        "primeiro_media": i0["media"],
        "plataformas_nacionais": [k for k in ("99", "Uber") if pl.get(k)],
        "aplicativos_locais": [x for x in loc.split(", ") if x] if loc else [],
    }


def posicao_regional(posicoes: dict) -> dict | None:
    """Indicadores agrupados pela posição do município entre os doze."""
    if not posicoes:
        return None
    por: dict = {}
    for k, v in posicoes.items():
        por.setdefault(v["posicao"], []).append(k)
    return {"por_posicao": dict(sorted(por.items())),
            "melhor_posicao": min(por), "pior_posicao": max(por),
            "todas_ate_a_quarta": max(por) <= 4}


# ══════════════════════════════════════════════════════════════════════════════
# CONJUNTO POR MUNICÍPIO
# ══════════════════════════════════════════════════════════════════════════════
def indicadores_municipais(m, ctx=None, iso=None, desl=None, sit=None,
                           perf=None, avaliacoes=None, ligacoes=None,
                           cx=None, posicoes=None) -> dict:
    """Todos os indicadores do município. Insumo não informado é lido."""
    ctx = contexto(m) if ctx is None else ctx
    iso = isocronas(m) if iso is None else iso
    desl = deslocamento(m) if desl is None else desl
    sit = situacao(m) if sit is None else sit
    perf = perfil(m) if perf is None else perf
    av = ic.carregar_avaliacoes(m) if avaliacoes is None else avaliacoes
    lig = ligacoes_onibus(m, ctx) if ligacoes is None else ligacoes
    rede = rede_entre_municipios(m, iso)
    return {
        "fronteira_internacional": fronteira_internacional(perf, sit),
        "municipio_mais_proximo": municipio_mais_proximo(iso),
        "alcance_rodoviario": alcance_rodoviario(iso),
        "tempo_ate_capital": tempo_ate_capital(m, iso, sit),
        "cidades_em_frente": cidades_em_frente(m, iso),
        "fronteiras_mais_proximas": fronteiras_mais_proximas(iso),
        "eixos_rodoviarios": eixos_rodoviarios(ctx),
        "trafego_de_acesso": trafego_de_acesso(ctx),
        "modos_de_chegada": modos_de_chegada(m, ctx, av),
        "infraestrutura_nautica": infraestrutura_nautica(m, ctx),
        "travessias": travessias(m, ctx, av),
        "onibus_interestadual": onibus_interestadual(ctx),
        "ligacoes_onibus": lig,
        "resumo_ligacoes_onibus": resumo_ligacoes_onibus(m, lig, iso),
        "rede_entre_municipios": rede,
        "resumo_rede": resumo_rede(m, rede),
        "baldeacoes": baldeacoes(m),
        "rede_aerea": rede_aerea(ctx, lig),
        "distancia_dos_atrativos": distancia_dos_atrativos(desl),
        "deslocamento_interno": deslocamento_interno(desl),
        "resumo_conectividade": resumo_conectividade(m, cx),
        "posicao_regional": posicao_regional(
            posicoes_do_municipio(m) if posicoes is None else posicoes),
    }


# ══════════════════════════════════════════════════════════════════════════════
# TABELAS
# ══════════════════════════════════════════════════════════════════════════════
def _celula(v):
    """Listas em uma célula, separadas por ponto e vírgula; pares, 'a: b'."""
    if isinstance(v, dict):
        return "; ".join(f"{k}: {_celula(x)}" for k, x in v.items())
    if isinstance(v, (list, tuple, set)):
        return "; ".join(
            (f"{x[0]}: {x[1]}" if isinstance(x, (list, tuple)) and len(x) == 2
             else str(x)) for x in v)
    return v


def _plano(d: dict | None, prefixo: str = "") -> dict:
    return {f"{prefixo}{k}": _celula(v) for k, v in (d or {}).items()}


def tabelas(indicadores: dict) -> dict:
    """{aba: DataFrame} a partir de {slug: indicadores_municipais(m)}."""
    import pandas as pd

    t: dict[str, list] = {k: [] for k in (
        "localizacao", "tempos_fronteira", "rodovias", "trafego",
        "modos_de_chegada", "nautica_travessias", "onibus_interestadual",
        "onibus_ligacoes", "onibus_resumo", "rede_municipios",
        "rede_municipios_resumo", "baldeacoes", "aereo", "atrativos",
        "deslocamento_interno", "conectividade", "posicao_regional")}
    for slug, ind in indicadores.items():
        m = POR_SLUG[slug]
        base = {"slug": slug, "municipio": m.nome, "uf": m.uf}
        t["localizacao"].append({
            **base, **_plano(ind["fronteira_internacional"]),
            **_plano(ind["municipio_mais_proximo"], "mais_proximo_"),
            "municipios_ate_2h": _celula(ind["alcance_rodoviario"]),
            **_plano(ind["tempo_ate_capital"], "capital_")})
        for tipo, chave_ in (("cidade em frente", "cidades_em_frente"),
                             ("passagem mais próxima",
                              "fronteiras_mais_proximas")):
            for x in ind[chave_]:
                t["tempos_fronteira"].append({**base, "tipo": tipo, **x})
        e = ind["eixos_rodoviarios"]
        if e:
            t["rodovias"].append({
                **base, "eixos_federais": len(e["eixos_federais"]),
                "rodovias_federais": _celula(
                    ["/".join(x["rodovias"]) for x in e["eixos_federais"]]),
                "km_por_eixo": _celula([x["km"] for x in e["eixos_federais"]]),
                "estaduais": _celula(e["estaduais"]),
                "rodovias_estaduais": len(e["estaduais"]),
                "estaduais_km": e["estaduais_km"], "pontes": e["pontes"]})
        t["trafego"].append({**base, **_plano(ind["trafego_de_acesso"])})
        t["modos_de_chegada"].append({**base, **ind["modos_de_chegada"]})
        t["nautica_travessias"].append({
            **base, **_plano(ind["infraestrutura_nautica"]),
            **_plano(ind["travessias"], "fronteira_")})
        if ind["onibus_interestadual"]:
            t["onibus_interestadual"].append(
                {**base, **ind["onibus_interestadual"]})
        for x in ind["ligacoes_onibus"] or []:
            t["onibus_ligacoes"].append({
                **base, **x, "horas": horas_de_duracao(x["duracao"]),
                "horas_hm": horas_de_duracao_hm(x)})
        t["onibus_resumo"].append({**base,
                                   **_plano(ind["resumo_ligacoes_onibus"])})
        for x in (ind["rede_entre_municipios"] or {}).get("municipios", []):
            t["rede_municipios"].append({**base, **_plano(
                {("destino" if k == "municipio" else
                  "uf_destino" if k == "uf" else k): v
                 for k, v in x.items()})})
        if ind["resumo_rede"]:
            t["rede_municipios_resumo"].append({**base,
                                                **_plano(ind["resumo_rede"])})
        b = ind["baldeacoes"]
        if b:
            for cidade, destinos in b["cidades_de_troca"].items():
                for dest in destinos:
                    t["baldeacoes"].append({
                        **base, "cidade_de_troca": cidade, "destino": dest,
                        "cidade_principal": cidade == b["cidade_principal"],
                        "espera_destino": b["espera_destino"],
                        "espera": b["espera"], "espera_h": b["espera_h"]})
        if ind["rede_aerea"]:
            t["aereo"].append({**base, **_plano(ind["rede_aerea"])})
        for x in ind["distancia_dos_atrativos"] or []:
            t["atrativos"].append({**base, **x})
        if ind["deslocamento_interno"]:
            t["deslocamento_interno"].append(
                {**base, **ind["deslocamento_interno"]})
        if ind["resumo_conectividade"]:
            t["conectividade"].append(
                {**base, **_plano(ind["resumo_conectividade"])})
        p = ind["posicao_regional"]
        if p:
            for pos, nomes in p["por_posicao"].items():
                for nome in nomes:
                    t["posicao_regional"].append({
                        **base, "indicador": nome, "posicao": pos,
                        "todas_ate_a_quarta": p["todas_ate_a_quarta"]})
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
        ind[m.slug] = indicadores_municipais(m)
        print(f"   {m.nome_uf}")
    saida.mkdir(parents=True, exist_ok=True)
    arq = saida / "indicadores_municipais.xlsx"
    with pd.ExcelWriter(arq, engine="openpyxl") as w:
        for aba, df in tabelas(ind).items():
            df.to_excel(w, sheet_name=aba, index=False)
    print(f"{len(ind)} municípios -> {arq}")
