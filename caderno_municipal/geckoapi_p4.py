# -*- coding: utf-8 -*-
"""
Oferta de onibus da ClickBus, pela GeckoAPI.

A ANTT regula o transporte interestadual: a ligacao dentro do estado nao
aparece na base dela senao como secao de linha interestadual vendida em
trecho, com o numero de passagens e nenhuma outra informacao. A consulta a
oferta traz as partidas do dia, a duracao da viagem, a faixa de preco e as
empresas que operam a ligacao.

A GeckoAPI expoe a listagem da ClickBus como `clickbus.com.br:plp`: cidade
e UF de origem, cidade e UF de destino, data. Um credito por requisicao.

    CHAVE
        variavel de ambiente GECKOAPI_KEY, ou GECKOAPI_KEYS com mais de uma
        chave separada por virgula. Nunca em arquivo do projeto.

    DATA
        variavel de ambiente GECKOAPI_DATA, no formato AAAA-MM-DD. Sem ela,
        vale 2026-09-30, a data da coleta guardada no cache, e a execucao se
        reproduz a partir dele. Data ja passada so se le do cache: se uma
        consulta para ela precisar ir a API, a execucao para, porque a
        resposta viria vazia e seria gravada como ausencia de oferta.

    ORCAMENTO
        `totalResults` ja traz o numero de partidas do dia, e a primeira
        pagina traz vinte delas. Paginar custaria outro credito para
        detalhar partidas que nao mudam a leitura: uma pagina por par.

SAIDA
    02_Dados_Municipais/oferta_clickbus/consulta_geckoapi_<slug>.json
        resumo por destino para a data da coleta. Nao e o registro
        oferta_clickbus_<slug>.json lido por indicadores_municipais_p4, que
        traz mais de uma data e os grupos de destinos e nao e gerado aqui.

USO
    python geckoapi_p4.py --plano          so imprime o que seria gasto
    python geckoapi_p4.py                  executa
    python geckoapi_p4.py 02_Medianeira_PR
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata
from datetime import date

import requests

from comum import DIR_DADOS, MUNICIPIOS, POR_SLUG, PRODUCAO

URL = "https://api.geckoapi.com.br/v1/extract"
# Uma ou mais chaves: quando o saldo de uma se esgota, a seguinte e usada.
CHAVES = [c.strip() for c in
          os.environ.get("GECKOAPI_KEYS",
                         os.environ.get("GECKOAPI_KEY", "")).split(",")
          if c.strip()]
_ATUAL = {"i": 0}
CACHE = DIR_DADOS / "cache" / "geckoapi"
SAIDA = DIR_DADOS / "oferta_clickbus"

# Data da coleta (GECKOAPI_DATA, AAAA-MM-DD). O padrao e a da coleta guardada
# no cache, uma quarta-feira: dia util tipico, longe o bastante para a grade
# estar publicada e perto o bastante para nao cair em ferias ou feriado.
DIA_PADRAO = "2026-09-30"


def _dia_da_coleta() -> date:
    bruto = (os.environ.get("GECKOAPI_DATA") or DIA_PADRAO).strip()
    try:
        return date.fromisoformat(bruto)
    except ValueError:
        raise SystemExit("GECKOAPI_DATA deve estar no formato AAAA-MM-DD "
                         f"(recebido: {bruto!r})") from None


DIA = _dia_da_coleta()


def _data_passada(dia: date) -> str:
    """Mensagem para a consulta fora do cache numa data que já passou."""
    return (f"A data da coleta ({dia.isoformat()}) já passou e a consulta não "
            "está no cache: a API devolveria a listagem vazia, gravada como "
            "ausência de oferta. Defina GECKOAPI_DATA (AAAA-MM-DD) com uma "
            "data de hoje em diante, ou restaure o cache dessa data.")


# Onde a ANTT nao alcanca. Para Bonito e Porto Murtinho, que nao tem
# nenhuma linha interestadual regulada, os destinos vem dos corredores
# intermunicipais da AGEMS.
FALLBACK = {
    "11_Bonito_MS": [("Campo Grande", "MS"), ("Jardim", "MS"),
                     ("Dourados", "MS"), ("Bodoquena", "MS")],
    "09_Porto_Murtinho_MS": [("Campo Grande", "MS"), ("Jardim", "MS"),
                             ("Bonito", "MS"), ("Dourados", "MS")],
}
# A capital do estado entra sempre: e o destino que estrutura a rede
# estadual, e e justamente o que a ANTT nao cobre.
CAPITAL = {"PR": ("Curitiba", "PR"), "MS": ("Campo Grande", "MS"),
           "SC": ("Florianopolis", "SC")}


def chave_atual():
    return CHAVES[_ATUAL["i"]] if CHAVES else None


def creditos(chave=None):
    r = requests.get("https://api.geckoapi.com.br/v1/me/credits",
                     headers={"X-API-Key": chave or chave_atual() or ""},
                     timeout=60)
    return r.json() if r.status_code == 200 else {"erro": r.status_code}


def sem_acento(s: str) -> str:
    t = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in t if not unicodedata.combining(c))


def _arq(o, ou, d, du, dia):
    CACHE.mkdir(parents=True, exist_ok=True)
    nome = f"{o}-{ou}__{d}-{du}__{dia}.json".replace(" ", "_").lower()
    return CACHE / sem_acento(nome)


def consultar(origem, uf_o, destino, uf_d, dia=DIA, forcar=False):
    """Uma consulta, um crédito. O cache evita repetir o mesmo par."""
    p = _arq(origem, uf_o, destino, uf_d, dia.isoformat())
    if p.exists() and not forcar:
        return json.loads(p.read_text("utf-8")), True
    if dia < date.today():
        raise RuntimeError(f"{origem}/{uf_o} → {destino}/{uf_d}: "
                           + _data_passada(dia))
    if not CHAVES:
        raise RuntimeError("defina GECKOAPI_KEYS no ambiente")
    corpo = {"target": "clickbus.com.br", "type": "plp",
             "originCity": sem_acento(origem), "originState": uf_o,
             "destinationCity": sem_acento(destino), "destinationState": uf_d,
             "departureDate": dia.isoformat()}

    class _Queda:
        """Queda de rede com cara de resposta 599.

        O laço de repetição olha `status_code`; sem isto, uma conexão
        derrubada pelo servidor escapava como exceção e matava a varredura
        inteira no meio, em vez de custar uma repetição.
        """

        status_code = 599

        def __init__(self, ex):
            self.text = f"conexão caiu: {str(ex)[:160]}"

    def _pede():
        try:
            return requests.post(URL, timeout=240, json=corpo,
                                 headers={"X-API-Key": chave_atual(),
                                          "Content-Type": "application/json"})
        except requests.RequestException as ex:
            return _Queda(ex)

    r = _pede()
    # 402 é saldo esgotado: a conta seguinte assume e a consulta se repete
    while r.status_code == 402 and _ATUAL["i"] + 1 < len(CHAVES):
        _ATUAL["i"] += 1
        print(f"   saldo esgotado; agora na chave {_ATUAL['i'] + 1} de "
              f"{len(CHAVES)}", flush=True)
        r = _pede()
    # 5xx é falha do provedor, e o crédito é estornado. Insistir vale a pena:
    # três das treze consultas de Foz do Iguaçu voltaram 502 na primeira
    # tentativa, e tratá-las como ausência de oferta seria registrar que
    # Curitiba não tem ônibus para lá.
    for espera in (8, 20, 45):
        if r.status_code < 500:
            break
        print(f"   {'queda de rede' if r.status_code == 599 else 'HTTP '
              + str(r.status_code)} em {destino}; nova tentativa em "
              f"{espera}s", flush=True)
        time.sleep(espera)
        r = _pede()
    if r.status_code != 200:
        return {"erro": r.status_code, "corpo": r.text[:300]}, False
    d = r.json()
    p.write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    return d, False


def resumir(resposta) -> dict:
    """A ligação em uma linha: partidas no dia, duração, preço, viação.

    A viagem direta manda. Uma conexão montada pela plataforma entre duas
    cidades que não se ligam diretamente não é a mesma coisa, e dizer que há
    ônibus para lá quando o que há é baldeação seria falsear a ligação.
    """
    # A falha nunca vira zero: "não consegui perguntar" e "perguntei e não
    # há" são coisas diferentes, e só a segunda é achado.
    if (resposta or {}).get("erro"):
        return {"falhou": True, "erro_http": resposta["erro"]}
    d = (resposta or {}).get("data") or {}
    itens = d.get("items") or []
    if not itens:
        return {"partidas_dia": 0, "sem_oferta": True,
                "url_resolvida": d.get("url", "")}
    diretas = [x for x in itens if x.get("type") == "direct"]
    base = diretas or itens
    precos = [float(x["price"]) for x in base if x.get("price") is not None]
    dur = sorted({str(x.get("durationText") or "") for x in base} - {""})
    return {
        "url_resolvida": d.get("url", ""),
        "partidas_dia": int(d.get("totalResults") or len(itens)),
        "na_pagina": len(itens),
        "diretas_na_pagina": len(diretas),
        "somente_com_conexao": not diretas,
        "duracao_min": dur[0] if dur else "",
        "duracao_max": dur[-1] if dur else "",
        "preco_min": round(min(precos), 2) if precos else None,
        "preco_max": round(max(precos), 2) if precos else None,
        "viacoes": sorted({str((x.get("travelCompany") or {}).get("name"))
                           for x in base} - {"None"}),
        "classes": sorted({str((x.get("serviceClass") or {}).get("name"))
                           for x in base} - {"None"}),
        "primeira_partida": min((str(x["departure"]["time"])[:5]
                                 for x in base), default=""),
        "ultima_partida": max((str(x["departure"]["time"])[:5]
                               for x in base), default=""),
    }


def _antt(slug):
    import pandas as pd
    M = POR_SLUG[slug]
    b = pd.read_csv(PRODUCAO / "08_transporte_coletivo_rodoviarias_clickbus"
                    / "consolidado_final_01_09_2026.csv", sep=";")
    alvo = f"{M.nome}/{M.uf}"
    fl = b[(b.ponto_origem_viagem == alvo) | (b.ponto_destino_viagem == alvo)]
    fl = fl.assign(outro=fl.ponto_origem_viagem.where(
        fl.ponto_destino_viagem == alvo, fl.ponto_destino_viagem))
    ag = (fl[fl.outro != alvo].groupby("outro").quantidade_bilhetes.sum()
          .sort_values(ascending=False))
    saida = []
    for x in ag.index:
        nome, _, uf = str(x).rpartition("/")
        if nome:
            saida.append((nome, uf))
    return saida


# As cidades que o nome do corredor nomeia. A camada do DER-PR e da AGEMS
# descreve o campo proximo melhor que a ANTT, cujos registros PR-PR sao
# secoes de linha interestadual: Foz do Iguacu-Cascavel aparece la com tres
# passagens no ano, e o corredor tem vinte partidas por dia.
def _cidades_do_corredor(slug) -> list:
    import bases_p4 as bp
    import intermunicipal_p4 as im
    M = POR_SLUG[slug]
    mun = bp.municipios()
    alvo = mun[mun.CD_MUN == M.codigo_ibge]
    if alvo.empty:
        return []
    sub = im.do_municipio(alvo.geometry.iloc[0], bp.CRS_MAPA)
    if sub is None:
        return []
    conhecidas = {sem_acento(m.nome).lower(): (m.nome, m.uf)
                  for m in MUNICIPIOS}
    extras = {"cascavel": ("Cascavel", "PR"), "toledo": ("Toledo", "PR"),
              "curitiba": ("Curitiba", "PR"), "dourados": ("Dourados", "MS"),
              "jardim": ("Jardim", "MS"), "realeza": ("Realeza", "PR"),
              "maracaju": ("Maracaju", "MS"),
              "santa helena": ("Santa Helena", "PR"),
              "bodoquena": ("Bodoquena", "MS")}
    saida = []
    for r in sub.itertuples():
        # "Tronco Oeste PR: Foz do Iguaçu ↔ Cascavel" -> os dois extremos
        corpo = str(r.nome_linha).split(":", 1)[-1]
        for pedaco in re.split(r"[↔➔>]+", corpo):
            chave = sem_acento(pedaco).strip().lower().rstrip(".")
            alvo_c = conhecidas.get(chave) or extras.get(chave)
            if alvo_c and alvo_c not in saida:
                saida.append(alvo_c)
    return saida


# No Parana o destino nao precisa ser adivinhado: o DER-PR diz quais linhas
# servem cada municipio, e o outro extremo de cada uma e o destino a
# consultar. Onde nao ha regulador com consulta aberta — Mato Grosso do Sul
# e Santa Catarina — ficam os corredores e a bilhetagem da ANTT.
_DER = (DIR_DADOS / "der_pr" / "consulta_linhas_der_pr.json")
_DET = (DIR_DADOS / "der_pr" / "linhas_detalhe_der_pr.json")
_UF_CIDADE = {"STA TEREZ. ITAIPU": ("Santa Terezinha de Itaipu", "PR")}


def destinos_do_der(slug) -> list:
    """Os destinos que o DER-PR registra para o município."""
    if not (_DER.exists() and _DET.exists()):
        return []
    con = json.loads(_DER.read_text("utf-8")).get(slug) or []
    det = json.loads(_DET.read_text("utf-8"))
    M = POR_SLUG[slug]
    eu = sem_acento(M.nome).upper()
    saida = []
    for r in con:
        nome = (det.get(r["url"]) or {}).get("linha", "")
        m = re.match(r"^\S+\s+(.*)$", nome)
        if not m:
            continue
        pontas = [re.sub(r"\s*\(.*$", "", x).strip()
                  for x in re.split(r"\s+-\s+", m.group(1))]
        outro = [x for x in pontas if eu not in sem_acento(x).upper()]
        if not outro:
            continue
        bruto = outro[0].strip()
        alvo = _UF_CIDADE.get(bruto.upper(), (bruto.title(), M.uf))
        if alvo not in saida:
            saida.append(alvo)
    return saida


def destinos(slug, quantos=5) -> list:
    """Para onde perguntar, com o crédito contado.

    Perto primeiro, e o perto vem dos corredores intermunicipais: é ali que
    a ANTT não enxerga. Depois a capital do estado, que estrutura a rede
    estadual. Só então o destino de maior volume, que a ANTT já descreve em
    passagens e tarifa mas não em duração nem em frequência.
    """
    M = POR_SLUG[slug]
    do_der = destinos_do_der(slug)
    if do_der:
        return do_der[:quantos] if quantos else do_der
    antt = _antt(slug) or []
    estudo = {sem_acento(m.nome).lower() for m in MUNICIPIOS}
    vizinhos_estudo = [(n, u) for n, u in antt
                       if sem_acento(n).lower() in estudo]
    longe = [(n, u) for n, u in antt if u != M.uf
             and sem_acento(n).lower() not in estudo]
    ordem = (_cidades_do_corredor(slug) + vizinhos_estudo
             + [CAPITAL.get(M.uf)] + longe + FALLBACK.get(slug, []))
    escolha: list = []
    for item in ordem:
        if not item:
            continue
        if sem_acento(item[0]).lower() == sem_acento(M.nome).lower():
            continue
        if item not in escolha:
            escolha.append(item)
        if len(escolha) >= quantos:
            break
    return escolha


def plano(slugs, quantos=5) -> list:
    return [(s, d, u) for s in slugs for d, u in destinos(s, quantos)]


def coletar(slugs, quantos=5, pausa=2.0):
    SAIDA.mkdir(parents=True, exist_ok=True)
    gasto = 0
    for slug in slugs:
        M = POR_SLUG[slug]
        saida = {"slug": slug, "municipio": M.nome_uf, "dia": DIA.isoformat(),
                 "fonte": "ClickBus, via GeckoAPI", "ligacoes": []}
        for nome, uf in destinos(slug, quantos):
            resp, do_cache = consultar(M.nome, M.uf, nome, uf)
            if not do_cache:
                gasto += 1
                time.sleep(pausa)
            r = resumir(resp)
            r.update(cidade=nome, uf=uf)
            if "erro" in resp:
                r["erro"] = resp["erro"]
            saida["ligacoes"].append(r)
            print(f"   {M.nome} → {nome}/{uf}: "
                  f"{r.get('partidas_dia', 0)} partidas"
                  + (f", {r['duracao_min']}" if r.get("duracao_min") else "")
                  + (f", de R$ {r['preco_min']:.2f}"
                     if r.get("preco_min") else "")
                  + ("  [cache]" if do_cache else ""), flush=True)
        (SAIDA / f"consulta_geckoapi_{slug}.json").write_text(
            json.dumps(saida, ensure_ascii=False, indent=1), "utf-8")
    return gasto


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quantos = 5
    for a in sys.argv[1:]:
        if a.startswith("--n="):
            quantos = int(a.split("=")[1])
    alvos = args or [m.slug for m in MUNICIPIOS]
    p = plano(alvos, quantos)
    novos = [x for x in p
             if not _arq(POR_SLUG[x[0]].nome, POR_SLUG[x[0]].uf, x[1], x[2],
                         DIA.isoformat()).exists()]
    print(f"{len(p)} consultas, {len(novos)} ainda não em cache "
          f"= {len(novos)} créditos\n")
    for s in alvos:
        print(f"{POR_SLUG[s].nome_uf:26} "
              + " · ".join(f"{n}/{u}" for n, u in destinos(s, quantos)))
    if "--plano" in sys.argv:
        raise SystemExit(0)
    if novos and DIA < date.today():
        raise SystemExit(f"{len(novos)} consultas fora do cache. "
                         + _data_passada(DIA))
    print(f"\nsaldo antes: {creditos().get('currentCredits')}")
    g = coletar(alvos, quantos)
    print(f"\ngastos: {g} créditos · saldo: "
          f"{creditos().get('currentCredits')}")
