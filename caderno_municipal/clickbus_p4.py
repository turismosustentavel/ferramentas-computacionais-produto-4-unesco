# -*- coding: utf-8 -*-
"""
Oferta de onibus pela API de parceiros da ClickBus.

O acervo traz uma amostra de 19 rotas para os doze municipios, concentrada
em Foz do Iguacu: nove municipios ficam com nenhuma ou uma. A ANTT cobre os
doze em preco, volume e classe de servico, mas nao tem duracao nem partidas
por dia. Isso so vem da oferta.

A ClickBus publica API de parceiros documentada em
developer.clickbus.com.br. O caminho e:

    POST {base}/oauth/basic-token      credenciais -> accessToken
    GET  {base}/v4/places?name=...     nome -> slug canonico
    GET  {base}/v5/trips?from&to&departureDate

As credenciais vem do executivo de contas da ClickBus, por aplicacao, e
producao e homologacao sao separadas. Este modulo nunca as guarda em
codigo: le de variavel de ambiente e nunca as imprime.

    CLICKBUS_BASE    https://platform-bff-partners.stg.clickbus.net/partners/api
    CLICKBUS_SENHA   o valor do Authorization header do basic-token

Homologacao responde de segunda a sexta, das 6h as 20h, e fora disso
devolve 503. Os dados de homologacao sao de cenarios de teste: a coleta
que vale para o estudo e a de producao.

USO
    python clickbus_p4.py                      varre os doze municipios
    python clickbus_p4.py 02_Medianeira_PR     so um
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import date, timedelta

import requests

from comum import DIR_DADOS, MUNICIPIOS, POR_SLUG

BASE = os.environ.get(
    "CLICKBUS_BASE",
    "https://platform-bff-partners.stg.clickbus.net/partners/api").rstrip("/")
SENHA = os.environ.get("CLICKBUS_SENHA")
CACHE = DIR_DADOS / "cache" / "clickbus"
SAIDA = DIR_DADOS / "oferta_clickbus"
_TOKEN: dict = {}


class SemCredencial(RuntimeError):
    pass


def _cache(nome):
    CACHE.mkdir(parents=True, exist_ok=True)
    return CACHE / nome


def token() -> str:
    if not SENHA:
        raise SemCredencial(
            "defina CLICKBUS_SENHA (e CLICKBUS_BASE, se produção) com a "
            "credencial fornecida pelo executivo de contas da ClickBus")
    if _TOKEN.get("valor") and time.time() < _TOKEN.get("ate", 0):
        return _TOKEN["valor"]
    r = requests.post(f"{BASE}/oauth/basic-token",
                      headers={"Content-Type": "application/json",
                               "Authorization": SENHA},
                      json={"grant_type": "client_credentials"}, timeout=60)
    r.raise_for_status()
    d = r.json()
    valor = d.get("accessToken") or d.get("access_token")
    if not valor:
        raise RuntimeError(f"resposta sem accessToken: {sorted(d)}")
    # o token é de longa duração; uma hora de folga basta e evita renová-lo
    # a cada chamada
    _TOKEN.update(valor=valor, ate=time.time() + 3000)
    return valor


def _get(caminho, params, arquivo=None):
    if arquivo is not None:
        p = _cache(arquivo)
        if p.exists():
            return json.loads(p.read_text("utf-8"))
    r = requests.get(f"{BASE}{caminho}", params=params, timeout=90,
                     headers={"Authorization": f"Bearer {token()}"})
    if r.status_code == 503:
        raise RuntimeError("ambiente de homologação fora da janela "
                           "(seg-sex, 6h-20h)")
    r.raise_for_status()
    d = r.json()
    if arquivo is not None:
        _cache(arquivo).write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    return d


def lugares(termo: str) -> list:
    """Os lugares que respondem ao termo, com o slug canônico de cada um."""
    chave = "".join(c if c.isalnum() else "_" for c in termo.lower())
    return _get("/v4/places", {"name": termo, "limit": 20},
                f"places_{chave}.json")


def slug_da_cidade(nome: str, uf: str):
    """O slug que representa a cidade inteira, e não um terminal dela.

    Quando a cidade tem mais de um terminal, `useGroupByCity` marca a
    entrada que reúne todos. É essa que interessa ao caderno, porque a
    pergunta é sobre o município e não sobre uma plataforma.
    """
    achados = lugares(nome)
    if isinstance(achados, dict):
        achados = achados.get("places") or achados.get("data") or []
    alvo = [x for x in achados
            if f", {uf.upper()}" in str(x.get("name", ""))]
    if not alvo:
        return None
    grupo = [x for x in alvo if x.get("useGroupByCity")]
    return str((grupo or alvo)[0].get("slug") or "") or None


def viagens(de: str, para: str, dia: date) -> list:
    """As partidas ofertadas naquele dia, entre os dois slugs."""
    d = _get("/v5/trips",
             {"from": de, "to": para, "departureDate": dia.isoformat()},
             f"trips_{de}__{para}__{dia.isoformat()}.json")
    if isinstance(d, list):
        d = d[0] if d else {}
    return (d or {}).get("departures") or []


def resumir(partidas: list) -> dict:
    """A ligação em uma linha: quantas partidas, quanto tempo, a que preço.

    A viagem direta manda: quando existe, é ela que descreve a ligação. Uma
    conexão montada pela plataforma entre duas cidades que não se ligam
    diretamente não é a mesma coisa, e dizer que há ônibus para lá quando o
    que há é baldeação em Cascavel seria falsear a ligação.
    """
    if not partidas:
        return {}
    diretas = [p for p in partidas if p.get("type") == "direct"]
    base = diretas or partidas
    precos = [float(p["price"]) for p in base if p.get("price") is not None]
    return {
        "partidas_dia": len(base),
        "diretas": len(diretas),
        "duracao": min((str((p.get("duration") or {}).get("hours") or "")
                        for p in base), default=""),
        "preco_min": round(min(precos), 2) if precos else None,
        "preco_max": round(max(precos), 2) if precos else None,
        "viacoes": sorted({str((p.get("travelCompany") or {}).get("name"))
                           for p in base} - {"None"}),
        "classes": sorted({str((p.get("serviceClass") or {}).get("name"))
                           for p in base} - {"None"}),
        "somente_com_conexao": not diretas,
    }


def destinos_da_antt(slug: str, quantos: int = 12) -> list:
    """Para onde perguntar: as ligações que a ANTT registra no município.

    Perguntar à ClickBus todos os destinos do Brasil seria caro e inútil.
    A bilhetagem da ANTT já diz para onde se viaja a partir dali, e a
    oferta responde quanto custa e quanto demora cada uma dessas.
    """
    import pandas as pd
    from comum import PRODUCAO
    M = POR_SLUG[slug]
    b = pd.read_csv(PRODUCAO / "08_transporte_coletivo_rodoviarias_clickbus"
                    / "consolidado_final_01_09_2026.csv", sep=";")
    alvo = f"{M.nome}/{M.uf}"
    fl = b[(b.ponto_origem_viagem == alvo) | (b.ponto_destino_viagem == alvo)]
    fl = fl.assign(outro=fl.ponto_origem_viagem.where(
        fl.ponto_destino_viagem == alvo, fl.ponto_destino_viagem))
    ag = (fl[fl.outro != alvo].groupby("outro").quantidade_bilhetes.sum()
          .sort_values(ascending=False))
    return [str(x) for x in ag.head(quantos).index]


def coletar(slug: str, dias=None) -> dict:
    """A oferta do município: um dia útil e um sábado, por padrão.

    Dois dias porque partida por dia não é constante: a linha de fim de
    semana não aparece na quarta-feira, e a de dia útil rareia no sábado.
    """
    M = POR_SLUG[slug]
    if dias is None:
        h = date.today()
        qua = h + timedelta(days=(2 - h.weekday()) % 7 + 7)
        dias = [qua, qua + timedelta(days=3)]
    de = slug_da_cidade(M.nome, M.uf)
    if not de:
        return {"slug": slug, "erro": "cidade não encontrada em /v4/places"}
    saida = {"slug": slug, "municipio": M.nome_uf, "origem": de,
             "dias": [d.isoformat() for d in dias], "ligacoes": []}
    for destino in destinos_da_antt(slug):
        nome, uf = destino.rsplit("/", 1)
        para = slug_da_cidade(nome, uf)
        if not para:
            continue
        por_dia = {}
        for d in dias:
            try:
                por_dia[d.isoformat()] = resumir(viagens(de, para, d))
            except Exception as ex:                          # noqa: BLE001
                por_dia[d.isoformat()] = {"erro": str(ex)[:120]}
        saida["ligacoes"].append({"cidade": nome, "uf": uf, "slug": para,
                                  "por_dia": por_dia})
        print(f"   {M.nome} -> {destino}: "
              f"{por_dia[dias[0].isoformat()].get('partidas_dia', 0)} "
              "partidas no dia útil")
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / f"oferta_clickbus_{slug}.json").write_text(
        json.dumps(saida, ensure_ascii=False, indent=1), "utf-8")
    return saida


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    alvos = sys.argv[1:] or [m.slug for m in MUNICIPIOS]
    try:
        token()
    except SemCredencial as ex:
        print(f"Sem credencial: {ex}")
        raise SystemExit(1)
    for s in alvos:
        print(POR_SLUG[s].nome_uf)
        coletar(s)
