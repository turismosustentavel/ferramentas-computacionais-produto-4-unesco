# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMAÇÕES POR MUNICÍPIO | PRODUTO 4
LOCALIZAÇÃO DO MUNICÍPIO: POSIÇÃO NO ESTADO, CAPITAL E FRONTEIRA
================================================================================
Calcula, por município, as medidas de localização em relação ao estado, à
capital estadual e à fronteira internacional.

MEDIDAS (metricas_situacao_<slug>.json)
    posicao_no_estado      rumo do município dentro da UF: norte, sul, leste,
                           oeste, um dos quatro colaterais ou "porção central"
    extremo_no_estado      verdadeiro quando o município fica na borda da UF
    capital                capital do estado
    distancia_capital_km   distância em linha reta até a capital, em km
                           inteiros
    distancia_linha_internacional_km
                           menor distância entre o território municipal e o
                           contorno do país, em km com uma casa; zero quando o
                           município toca a linha
    distancia_paises_km    menor distância até cada país vizinho (Argentina,
                           Bolívia, Paraguai, Uruguai), em km com uma casa;
                           só para os municípios com distância à linha
                           diferente de zero

MÉTODO
    Medidas em SIRGAS 2000 / Brazil Polyconic (EPSG:5880).
    Ponto do município: ponto interior do polígono municipal
        (representative_point), que cai sempre dentro do território.
    Posição no estado: deslocamento do ponto do município em relação ao
        centro do envelope da UF, dividido pela meia largura (dx) e pela meia
        altura (dy) do envelope. Um eixo só é nomeado quando o deslocamento
        passa de LIMIAR_RUMO em módulo: dy acima, norte; dy abaixo do negativo,
        sul; o mesmo com dx para leste e oeste. Os dois eixos juntos dão o
        colateral; nenhum, "porção central".
    Extremo no estado: |dx| ou |dy| acima de LIMIAR_EXTREMO.
    Capital: distância entre o ponto interior do município e o do município
        da capital (CAPITAIS).
    Linha internacional: distância do polígono municipal ao contorno da
        união dos polígonos do país (BR_Pais_2025). O contorno inclui o
        litoral.
    Países vizinhos: distância do polígono municipal à união dos polígonos
        de cada país na camada de países da América do Sul; o nome do país
        vem do campo PAIS ou, quando em branco, do código FIPS (FIPS).

ENTRADAS (relativas a P4_DADOS)
    Levantamentos e Análises/Produto 4/01_Bases_Secundarias_Oficiais/Shapes/
        BR_Municipios_2025.zip, BR_UF_2025.zip, BR_Pais_2025.zip
            malhas do IBGE (2025), lidas por bases_p4
    Levantamentos e Análises/Produto 4/09_Base_Socioeconomica_Municipal/
        06_Cartografia_Tematica/america_do_sul_paises.gpkg
            países da América do Sul (campos PAIS e FIPS_CNTRY)

SAÍDAS
    Entregas/Produto 4/produção/Caderno de informações por município/
        02_Dados_Municipais/<slug>/metricas_situacao_<slug>.json

COMO EXECUTAR
    python localizacao_p4.py 08_Ponta_Pora_MS
    python localizacao_p4.py 02_Medianeira_PR 06_Guaira_PR

    O argumento é o slug de comum.MUNICIPIOS (um ou mais).

    Uso como módulo:
        import localizacao_p4 as lz
        from comum import POR_SLUG
        lz.metricas_situacao(POR_SLUG["02_Medianeira_PR"])

ORDEM
    Depende só das malhas oficiais. A saída é lida por
    indicadores_municipais_p4 (capital, distância à linha internacional e aos
    países vizinhos).
================================================================================
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd

sys.path.insert(0, str(Path(__file__).parent))
import bases_p4 as bp                                            # noqa: E402
from comum import (ACERVO, CRS_MAPA, DIR_DADOS, MUNICIPIOS,      # noqa: E402
                   POR_SLUG)

PAISES_AS = (ACERVO / "09_Base_Socioeconomica_Municipal" /
             "06_Cartografia_Tematica" / "america_do_sul_paises.gpkg")

# ══════════════════════════════════════════════════════════════════════════════
# PARÂMETROS
# ══════════════════════════════════════════════════════════════════════════════
# Deslocamento normalizado (de -1 a 1) a partir do qual o eixo é nomeado: um
# município central não recebe rumo por uma diferença pequena.
LIMIAR_RUMO = 0.18
# Deslocamento normalizado acima do qual o município está na borda da UF.
LIMIAR_EXTREMO = 0.75

# UF -> (código IBGE do município da capital, nome)
CAPITAIS = {"PR": (4106902, "Curitiba"),
            "MS": (5002704, "Campo Grande"),
            "SC": (4205407, "Florianópolis")}

PAISES_VIZINHOS = ["Argentina", "Paraguai", "Bolívia", "Uruguai"]

# A camada de países da América do Sul traz o nome em branco para vários
# registros; o código FIPS completa a identificação.
FIPS = {"AR": "Argentina", "BL": "Bolívia", "BR": "Brasil", "CI": "Chile",
        "CO": "Colômbia", "EC": "Equador", "FG": "Guiana Francesa",
        "GY": "Guiana", "NS": "Suriname", "PA": "Paraguai", "PE": "Peru",
        "UY": "Uruguai", "VE": "Venezuela"}

_cache: dict = {}


# ══════════════════════════════════════════════════════════════════════════════
# LEITURA
# ══════════════════════════════════════════════════════════════════════════════
def paises_america_do_sul() -> gpd.GeoDataFrame | None:
    """Países da América do Sul, com o nome resolvido pelo código FIPS, em
    EPSG:5880. None se a camada não existir."""
    if "paises_as" not in _cache:
        if not PAISES_AS.exists():
            _cache["paises_as"] = None
        else:
            g = gpd.read_file(PAISES_AS)
            g["nome"] = [
                (n if isinstance(n, str) and n.strip()
                 else FIPS.get(str(f).strip().upper()))
                for n, f in zip(g.get("PAIS"), g.get("FIPS_CNTRY"))
            ]
            _cache["paises_as"] = g[g.nome.notna()].to_crs(CRS_MAPA)
    return _cache["paises_as"]


# ══════════════════════════════════════════════════════════════════════════════
# MEDIDAS
# ══════════════════════════════════════════════════════════════════════════════
def rumo(dx: float, dy: float) -> str:
    """Rumo cardeal a partir do deslocamento normalizado no envelope da UF.
    Só nomeia o eixo que passa do limiar."""
    ns = ("norte" if dy > LIMIAR_RUMO else
          "sul" if dy < -LIMIAR_RUMO else "")
    lo = ("leste" if dx > LIMIAR_RUMO else
          "oeste" if dx < -LIMIAR_RUMO else "")
    if ns and lo:
        return {("norte", "leste"): "nordeste", ("norte", "oeste"): "noroeste",
                ("sul", "leste"): "sudeste", ("sul", "oeste"): "sudoeste"}[
            (ns, lo)]
    return ns or lo or "porção central"


def metricas_situacao(m, mun: gpd.GeoDataFrame | None = None) -> dict:
    """Medidas de localização do município. Vazio se a UF ou o município
    não estiverem na malha."""
    mun = bp.municipios() if mun is None else mun
    alvo = mun[mun.CD_MUN == m.codigo_ibge]
    uf = bp.ufs()
    uf_g = uf[uf.SIGLA_UF == m.uf]
    met: dict = {}
    if not (len(uf_g) and len(alvo)):
        return met

    # posição no estado
    x0, y0, x1, y1 = uf_g.total_bounds
    c = alvo.geometry.iloc[0].representative_point()
    dx = (c.x - (x0 + x1) / 2) / ((x1 - x0) / 2)
    dy = (c.y - (y0 + y1) / 2) / ((y1 - y0) / 2)
    met["posicao_no_estado"] = rumo(dx, dy)
    met["extremo_no_estado"] = bool(abs(dx) > LIMIAR_EXTREMO
                                    or abs(dy) > LIMIAR_EXTREMO)

    # distância em linha reta até a capital do estado
    cap = CAPITAIS.get(m.uf)
    gc = mun[mun.CD_MUN == cap[0]] if cap else None
    if gc is not None and len(gc):
        pc = gc.geometry.iloc[0].representative_point()
        met["capital"] = cap[1]
        met["distancia_capital_km"] = round(c.distance(pc) / 1000)

    # distância até o contorno do país
    pais = bp.pais()
    if len(pais):
        linha = pais.geometry.union_all().boundary
        d = alvo.geometry.iloc[0].distance(linha)
        met["distancia_linha_internacional_km"] = round(d / 1000, 1)

    # distância até cada país vizinho, quando o município não toca a linha
    pa = paises_america_do_sul()
    if pa is not None and met.get("distancia_linha_internacional_km"):
        a = alvo.geometry.iloc[0]
        met["distancia_paises_km"] = {
            p: round(a.distance(g.geometry.union_all()) / 1000, 1)
            for p, g in pa[pa.nome.isin(PAISES_VIZINHOS)].groupby("nome")}
    return met


# ══════════════════════════════════════════════════════════════════════════════
# EXECUÇÃO
# ══════════════════════════════════════════════════════════════════════════════
def arquivo(m) -> Path:
    return DIR_DADOS / m.slug / f"metricas_situacao_{m.slug}.json"


def gravar(m, met: dict) -> Path:
    arq = arquivo(m)
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(met, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    return arq


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
    mun = bp.municipios()
    for slug in args:
        m = POR_SLUG[slug]
        met = metricas_situacao(m, mun)
        print(f"{m.nome_uf}: {met}")
        print("   " + str(gravar(m, met)))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
