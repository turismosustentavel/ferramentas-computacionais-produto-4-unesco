# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
VERIFICACAO DAS DISTANCIAS REGISTRADAS NAS FICHAS DE CAMPO
================================================================================
As fichas de rodoviaria, aeroporto e aduana pedem a distancia aproximada do
equipamento ate o centro, o principal atrativo, o CAT mais proximo e o
terminal de transporte (urbano ou rodoviario). Este script confere cada valor
registrado contra a posicao real:

    equipamento   coordenada do ponto de afericao vinculado a ficha
    referencia    geocodificada (Nominatim/OSM) a partir do que a propria
                  ficha nomeia; sem nome, a referencia adotada e declarada
    distancia     em linha reta e pela malha viaria (OSRM, perfil carro)

Distancia de referencia: a viaria. Sem rota, ou com rota acima de 2,2 vezes
a linha reta (o roteador contornou o sitio), a referencia e a linha reta
x 1,3, marcada como estimada.

Veredito:
    CONSISTENTE            com rota: o registrado fica a ate 1 km ou 35 % da
                           referencia; com referencia estimada: o registrado
                           fica entre 0,8 x reta - 0,5 km e 1,8 x reta + 1 km
    DIVERGENTE - MODERADA  fora disso, com razao registrado/referencia entre
                           0,5 e 2,0
    DIVERGENTE - FORTE     razao fora de 0,5 a 2,0
    NAO VERIFICAVEL        a referencia nao pode ser localizada sem inventar
                           o que a equipe quis dizer

A cobertura - quantas fichas deixaram esses campos em branco - e registrada
junto, porque a ausencia tambem e resultado.

SAIDAS
    02_Dados_Municipais/verificacao_distancias_fichas.xlsx
    02_Dados_Municipais/verificacao_distancias_fichas.json
================================================================================
"""
from __future__ import annotations

import io
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import atrativos_p4 as ap                                        # noqa: E402
import fichas_p4 as fp                                           # noqa: E402
from comum import CAMPO, DIR_DADOS, normalizar_municipio         # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CACHE = DIR_DADOS / "cache" / "geocodificacao_referencias.json"
CACHE.parent.mkdir(parents=True, exist_ok=True)
cache = json.loads(CACHE.read_text("utf-8")) if CACHE.exists() else {}
UA = {"User-Agent": "itaipu-parquetec-produto4/1.0"}

# campo da ficha -> (tipo de referencia, campo que a nomeia)
CAMPOS = {
    "Rodoviária": {
        "Distância aproximada até o principal atrativo turístico":
            ("atrativo", "Principal atrativo turístico "),
        "Distância aproximada até o centro": ("centro", "Identificação do centro"),
        "Distância até CAT (quando não existir)": ("cat", None),
        "Distância até terminal de transporte urbano": ("terminal_urbano", None),
    },
    "Aeroporto": {
        "Distância aproximada até o principal atrativo turístico (km)":
            ("atrativo", None),
        "Distância aproximada até o centro urbano (km)": ("centro", None),
        "Distância até CAT (quando não existir) (km)": ("cat", None),
    },
    "Aduana": {
        "Distância aproximada até o principal atrativo turístico (km)":
            ("atrativo", "Local definido como atrativo turístico"),
        "Distância aproximada até o centro (km)":
            ("centro", "Local definido como centro"),
        "Distância até CAT (quando não existir) (km)": ("cat", None),
        "Distância até terminal rodoviário (km)": ("rodoviaria", None),
    },
}
ROTULO = {"atrativo": "principal atrativo", "centro": "centro",
          "cat": "CAT mais próximo", "terminal_urbano": "terminal urbano",
          "rodoviaria": "terminal rodoviário"}


# ══════════════════════════════════════════════════════════════════════════════
# GEOGRAFIA
# ══════════════════════════════════════════════════════════════════════════════
def haversine(a, b) -> float:
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def rota(a, b) -> float | None:
    chave = f"osrm|{a[0]:.5f},{a[1]:.5f}|{b[0]:.5f},{b[1]:.5f}"
    if chave in cache:
        return cache[chave]
    url = ("http://router.project-osrm.org/route/v1/driving/"
           f"{a[1]},{a[0]};{b[1]},{b[0]}?overview=false")
    try:
        r = json.load(urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=30))
        km = round(r["routes"][0]["distance"] / 1000, 2) if r["code"] == "Ok" else None
    except Exception:
        km = None
    cache[chave] = km
    time.sleep(0.4)
    return km


def osm_no_municipio(filtro: str, cod_ibge: int) -> list[tuple]:
    """Feições do OSM dentro do polígono do município (IBGE).

    O recorte pelo polígono importa na fronteira: sem ele, Puerto Iguazú e
    Ciudad del Este entram como se fossem Foz do Iguaçu.
    """
    import bases_p4 as bp
    from shapely.geometry import Point
    mun = bp.municipios()
    poly = mun[mun.CD_MUN == cod_ibge].to_crs(4674).geometry.iloc[0]
    x0, y0, x1, y1 = poly.bounds
    chave = f"ovp|{filtro}|{cod_ibge}"
    if chave not in cache:
        q = (f"[out:json][timeout:25];(nwr{filtro}({y0},{x0},{y1},{x1}););"
             "out center tags;")
        for tentativa, srv in enumerate((
                "https://overpass-api.de/api/interpreter",
                "https://overpass-api.de/api/interpreter",
                "https://overpass.private.coffee/api/interpreter")):
            try:
                time.sleep(4 * tentativa)
                r = json.load(urllib.request.urlopen(urllib.request.Request(
                    srv, data=urllib.parse.urlencode({"data": q}).encode(),
                    headers=UA), timeout=60))
                cache[chave] = [[e.get("center", e).get("lat"),
                                 e.get("center", e).get("lon"),
                                 e.get("tags", {}).get("name")]
                                for e in r["elements"]]
                break
            except Exception:
                continue
        else:
            return None               # falha de consulta, nao ausencia
    return [tuple(e) for e in cache[chave]
            if e[0] is not None and poly.contains(Point(e[1], e[0]))]


def geocodificar(q: str):
    chave = f"nom|{q}"
    if chave in cache:
        return cache[chave]
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1})
    try:
        r = json.load(urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=30))
        res = ([float(r[0]["lat"]), float(r[0]["lon"]), r[0]["display_name"]]
               if r else None)
    except Exception:
        res = None
    cache[chave] = res
    time.sleep(1.1)                      # politica de uso do Nominatim
    return res


# ══════════════════════════════════════════════════════════════════════════════
# PONTOS DE REFERENCIA
# ══════════════════════════════════════════════════════════════════════════════
camada = gpd.read_file(CAMPO / "03_Pontos_Afericao" / "vetores_gis" /
                       "pontos_afericao_consolidados.geojson")


def ponto_da_camada(cidade: str, categoria: str):
    s = camada[(camada.cidade == cidade)
               & camada.categoria.astype(str).str.contains(categoria)]
    if not len(s):
        return None
    g = s.iloc[0]
    return (float(g.latitude), float(g.longitude), str(g.nome_ponto).strip())


def referencia(tipo: str, texto: str | None, municipio, uf: str, origem):
    """(lat, lon, descrição do que foi adotado) ou (None, None, motivo)."""
    cidade = municipio.nome
    if tipo == "centro":
        # a sede municipal e o centro; o nome dado pela equipe, quando
        # geocodificavel, e testado tambem e prevalece
        if texto and texto.lower() not in ("centro", "região central (bairro)",
                                           f"centro {cidade.lower()}"):
            g = geocodificar(f"{texto}, {cidade}, {uf}, Brasil")
            if g:
                return g[0], g[1], f"{texto} (OSM)"
        g = geocodificar(f"{cidade}, {uf}, Brasil")
        return (g[0], g[1], "sede municipal (OSM)") if g else (None, None,
                                                               "sede não localizada")
    if tipo == "rodoviaria":
        p = ponto_da_camada(cidade, "Terminal")
        return (p[0], p[1], p[2]) if p else (None, None, "sem rodoviária na camada")
    if tipo == "terminal_urbano":
        osm = osm_no_municipio('["amenity"="bus_station"]', municipio.codigo_ibge)
        if osm is None:
            return None, None, "consulta ao OSM indisponível — repetir"
        achados = [e for e in osm if e[2] and "urbano" in e[2].lower()]
        if achados:
            e = min(achados, key=lambda e: haversine(origem, (e[0], e[1])))
            return e[0], e[1], f"{e[2]} (OSM)"
        return None, None, "terminal urbano não mapeado no OSM"
    if tipo == "cat":
        # so vale CAT municipal; centro de visitantes de atrativo nao e CAT
        osm = osm_no_municipio('["tourism"="information"]', municipio.codigo_ibge)
        if osm is None:
            return None, None, "consulta ao OSM indisponível — repetir"
        achados = [e for e in osm
                   if e[2] and any(k in e[2].lower() for k in
                                   ("atendimento ao turista", "cat ",
                                    "informações turísticas",
                                    "informação turística"))]
        if achados:
            e = min(achados, key=lambda e: haversine(origem, (e[0], e[1])))
            return e[0], e[1], f"{e[2]} (OSM)"
        return (None, None, "nenhum CAT municipal mapeado no OSM; os pontos de "
                "informação existentes são centros de visitantes de atrativos")
    if tipo == "atrativo":
        t = (texto or "").lower()
        if "paraguai" in t:
            ponte = camada[(camada.cidade == cidade)
                           & camada.nome_ponto.astype(str).str.contains("Amizade")]
            if len(ponte):
                g = ponte.iloc[0]
                return (float(g.latitude), float(g.longitude),
                        "Ponte da Amizade — travessia para o Paraguai")
        if "argentina" in t:
            s = camada[(camada.municipio.astype(str).str.contains(
                "Dion|Barrac", regex=True))
                & camada.categoria.astype(str).str.contains("Aduana")]
            if len(s):
                g = s.iloc[0]
                return (float(g.latitude), float(g.longitude),
                        f"{str(g.nome_ponto).strip()} — fronteira com a Argentina")
        if not texto:
            # sem nome: o atrativo da hierarquia de relevancia mais proximo
            tab = ap.tabela(cidade)
            melhor = None
            for r in tab:
                g = geocodificar(f"{r['atrativo']}, {cidade}, {uf}, Brasil")
                if g:
                    d = haversine(origem, (g[0], g[1]))
                    if melhor is None or d < melhor[3]:
                        melhor = (g[0], g[1], r["atrativo"], d)
            if melhor:
                return (melhor[0], melhor[1],
                        f"{melhor[2]} — atrativo da hierarquia mais próximo; "
                        "a ficha não o nomeia")
            return None, None, "atrativo não nomeado"
        return None, None, f"referência “{texto}” sem localização inequívoca"
    return None, None, "tipo desconhecido"


# ══════════════════════════════════════════════════════════════════════════════
# VERIFICACAO
# ══════════════════════════════════════════════════════════════════════════════
vinc = pd.read_excel(DIR_DADOS / "vinculo_fichas_pontos.xlsx",
                     sheet_name="Vínculo")
vinc = vinc[vinc.vinculado]

linhas, cobertura = [], []
for form, campos in CAMPOS.items():
    tab = fp.tabela(form)
    for i, reg in tab.iterrows():
        linha_csv = i + 2
        v = vinc[(vinc["formulário"] == form) & (vinc.linha_csv == linha_csv)]
        mun_txt = reg.get("Município")
        m = normalizar_municipio(mun_txt)
        nome_eq = (v.iloc[0].ponto_vinculado if len(v) else
                   str(reg.get("Nome") or reg.get("Nome do aeroporto")
                       or reg.get("Nome da aduana")))
        preenchidos = 0
        for campo, (tipo, campo_nome) in campos.items():
            val = pd.to_numeric(str(reg.get(campo)).replace(",", "."),
                                errors="coerce")
            if pd.isna(val):
                continue
            preenchidos += 1
            texto = (str(reg.get(campo_nome)).strip()
                     if campo_nome and pd.notna(reg.get(campo_nome)) else None)
            base = {"municipio": m.nome_uf if m else mun_txt,
                    "cod_ibge": m.codigo_ibge if m else None,
                    "formulario": form, "linha_csv": linha_csv,
                    "equipamento": nome_eq,
                    "ordem": v.iloc[0].ordem if len(v) else None,
                    "campo": ROTULO[tipo], "coluna": campo,
                    "referencia_na_ficha": texto,
                    "registrado_km": float(val)}
            if not len(v):
                linhas.append({**base, "veredito": "NÃO VERIFICÁVEL",
                               "observacao": "ficha sem ponto vinculado"})
                continue
            origem = (float(v.iloc[0].lat), float(v.iloc[0].lon))
            if val == 0 and tipo == "atrativo":
                if texto:
                    linhas.append({**base, "referencia_adotada": texto,
                                   "veredito": "CONSISTENTE",
                                   "observacao": "o equipamento é a própria "
                                                 "porta do atrativo declarado"})
                else:
                    linhas.append({**base, "referencia_adotada": None,
                                   "veredito": "NÃO VERIFICÁVEL",
                                   "observacao": "atrativo não nomeado; 0 km "
                                                 "só se sustenta se o atrativo "
                                                 "for a própria travessia"})
                continue
            la, lo, desc = referencia(tipo, texto, m, m.uf, origem)
            if la is None:
                linhas.append({**base, "referencia_adotada": None,
                               "veredito": "NÃO VERIFICÁVEL",
                               "observacao": desc})
                continue
            reta = round(haversine(origem, (la, lo)), 2)
            viaria = rota(origem, (la, lo))
            obs = ""
            if viaria is None:
                obs = "rota indisponível; referência = linha reta × 1,3"
            elif reta > 0.3 and viaria / reta > 2.2:
                # desvio implausivel: o ponto caiu em patio, pista ou via
                # interna e o roteador contornou o sitio
                obs = (f"rota descartada ({viaria:g} km, {viaria / reta:.1f}× a "
                       "linha reta); referência = linha reta × 1,3")
                viaria = None
            ref_km = viaria if viaria is not None else round(reta * 1.3, 2)
            razao = val / ref_km if ref_km else None
            estimada = viaria is None
            if estimada and 0.8 * reta - 0.5 <= val <= 1.8 * reta + 1.0:
                # sem rota valida a referencia e so estimativa: diverge apenas
                # o que foge claramente da faixa plausivel sobre a linha reta
                ver = "CONSISTENTE"
            elif not estimada and abs(val - ref_km) <= max(1.0, 0.35 * ref_km):
                ver = "CONSISTENTE"
            elif razao and 0.5 <= razao <= 2.0:
                ver = "DIVERGENTE — MODERADA"
            else:
                ver = "DIVERGENTE — FORTE"
            linhas.append({**base, "referencia_adotada": desc,
                           "ref_lat": la, "ref_lon": lo,
                           "linha_reta_km": reta, "viaria_km": viaria,
                           "referencia_km": ref_km,
                           "razao_registrado_referencia":
                               round(razao, 2) if razao else None,
                           "veredito": ver, "observacao": obs})
        cobertura.append({"formulario": form, "linha_csv": linha_csv,
                          "municipio": m.nome_uf if m else mun_txt,
                          "equipamento": nome_eq,
                          "campos_de_distancia": len(campos),
                          "preenchidos": preenchidos})

CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), "utf-8")

df = pd.DataFrame(linhas)
cob = pd.DataFrame(cobertura)
destino = DIR_DADOS / "verificacao_distancias_fichas.xlsx"
with pd.ExcelWriter(destino) as w:
    df.to_excel(w, sheet_name="Verificação", index=False)
    cob.to_excel(w, sheet_name="Cobertura", index=False)
(DIR_DADOS / "verificacao_distancias_fichas.json").write_text(
    json.dumps({"verificacao": linhas, "cobertura": cobertura},
               ensure_ascii=False, indent=1, default=str), "utf-8")

pd.set_option("display.width", 220)
pd.set_option("display.max_colwidth", 46)
print(df[["municipio", "campo", "registrado_km", "referencia_km",
          "linha_reta_km", "viaria_km", "veredito", "referencia_adotada"]]
      .to_string(index=False))
print()
print(f"Fichas com campos de distância: {len(cob)} · com ao menos um "
      f"preenchido: {(cob.preenchidos > 0).sum()} · todos em branco: "
      f"{(cob.preenchidos == 0).sum()}")
print(df.veredito.value_counts().to_string())
print(f"\n→ {destino}")
