# -*- coding: utf-8 -*-
"""
Classe funcional da via em que cada ponto foi aferido.

A ficha de campo descreve a via pelo que se ve — cobertura, faixas, fluxo —,
mas nao diz que papel ela cumpre na malha. Isso esta no OpenStreetMap, na
etiqueta `highway`, que e uma hierarquia funcional: de `motorway` a
`residential`.

Consulta o Overpass num raio curto em volta de cada ponto e fica com a via
etiquetada mais proxima. O resultado vai para cache: a classe de uma rua nao
muda entre execucoes, e o Overpass nao deve ser consultado a toa.
"""
from __future__ import annotations

import json
import math
import time

import requests

from comum import DIR_DADOS

OVERPASS = ["https://overpass-api.de/api/interpreter",
            "https://lz4.overpass-api.de/api/interpreter",
            "https://z.overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter"]

# A etiqueta do OSM e o rotulo da classe funcional (o papel da via na malha,
# sem a palavra "via"). A ordem e a hierarquia: quando duas vias estao
# igualmente perto, vence a de maior papel na malha.
HIERARQUIA = [
    ("motorway", "expressa"),
    ("trunk", "ligação principal"),
    ("primary", "arterial primária"),
    ("secondary", "arterial secundária"),
    ("tertiary", "coletora"),
    ("unclassified", "local de ligação"),
    ("residential", "local"),
    ("living_street", "local"),
    ("service", "de serviço"),
    ("track", "não pavimentada"),
]
NOME = dict(HIERARQUIA)
ORDEM = {k: i for i, (k, _) in enumerate(HIERARQUIA)}
RAIO_M = 80


def _cache(slug: str):
    p = DIR_DADOS / "cache" / f"osm_classe_via_{slug}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _consulta(pontos: list[tuple[float, float]]) -> dict:
    """Uma só consulta para todos os pontos, em volta de cada um."""
    partes = "".join(
        f'way(around:{RAIO_M},{lat},{lon})["highway"];'
        for lat, lon in pontos)
    q = f"[out:json][timeout:120];({partes});out tags center;"
    for tentativa in range(3):
        for url in OVERPASS:
            try:
                r = requests.post(url, data={"data": q}, timeout=180,
                                  headers={"User-Agent": "CadernoP4/1.0"})
                if r.status_code == 200:
                    d = r.json()
                    if isinstance(d.get("elements"), list):
                        return d
            except Exception:                                # noqa: BLE001
                pass
        time.sleep(15 * (tentativa + 1))
    raise RuntimeError("Overpass indisponível: classe da via não obtida")


def _dist_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def classes(slug: str, pontos: dict[int, tuple[float, float]],
            forcar: bool = False) -> dict[str, dict]:
    """{número do ponto: {classe, rotulo, nome_da_via}} — com cache."""
    arq = _cache(slug)
    if arq.exists() and not forcar:
        guardado = json.loads(arq.read_text(encoding="utf-8"))
        if set(guardado) >= {str(k) for k in pontos}:
            return guardado

    d = _consulta([pontos[k] for k in sorted(pontos)])
    vias = []
    for el in d.get("elements", []):
        tags = el.get("tags") or {}
        via = tags.get("highway")
        c = el.get("center") or {}
        if via in ORDEM and c:
            vias.append((c["lat"], c["lon"], via, tags.get("name", "")))

    saida = {}
    for n, (lat, lon) in pontos.items():
        perto = [(v, nome, _dist_m(lat, lon, vlat, vlon))
                 for vlat, vlon, v, nome in vias
                 if _dist_m(lat, lon, vlat, vlon) <= RAIO_M * 3]
        if not perto:
            saida[str(n)] = {"classe": None, "rotulo": "", "via": ""}
            continue
        # Faixa de serviço e trilha não são "a via" que a ficha avalia: são
        # pátio de estacionamento, acesso de garagem, alça interna. Só valem
        # quando não há nenhuma via de circulação por perto.
        circulacao = [x for x in perto if x[0] not in ("service", "track")]
        perto = circulacao or perto
        # a mais próxima; empatando em 40 m, a de maior papel na malha
        perto.sort(key=lambda x: (round(x[2] / 40), ORDEM[x[0]]))
        v, nome, _ = perto[0]
        saida[str(n)] = {"classe": v, "rotulo": NOME[v], "via": nome}

    arq.write_text(json.dumps(saida, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    return saida
