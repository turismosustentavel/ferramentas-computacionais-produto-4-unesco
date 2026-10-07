# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMAÇÕES POR MUNICÍPIO | PRODUTO 4
DESLOCAMENTO INTERNO: ACTs, ATRATIVOS, TRAJETOS E SOBREPOSIÇÃO
================================================================================
Reúne, por município, as camadas e as medidas do deslocamento interno do
visitante: onde está a oferta de Atividades Características do Turismo
(ACTs), a que distância dela ficam os atrativos, quanto medem os trajetos
modelados entre o centro das ACTs e os atrativos e onde esses trajetos se
sobrepõem.

MEDIDAS (metricas_deslocamento_<slug>.json)
    municipio, codigo_ibge
    acts            total; área da envoltória convexa (km², uma casa);
                    distância de cada ACT ao centro: média, mediana e máxima
                    (km, uma casa); percentual a até RAIO_CURTO_KM e a até
                    RAIO_LONGO_KM (uma casa); coordenadas do centro
                    (EPSG:4674, seis casas)
    atrativos       total mantido no cálculo; postos distintos na hierarquia
                    (ord < 99); distância média e máxima ao centro em linha
                    reta (km, uma casa); os principais da hierarquia, com a
                    distância em linha reta e, onde a modelagem traçou a rota,
                    a extensão da rota mais curta até ele (km, uma casa); a
                    tabela de relevância (atrativos_p4.tabela); os atrativos
                    com coordenada corrigida e os que ficaram fora do
                    cálculo, com o motivo
    trajetos        total; extensão média, mediana, máxima e somada (km, uma
                    casa)
    sobreposicao    raio do agrupamento (fluxos_p4); agrupamentos
                    retidos; vértices do município; frequência máxima e
                    média (uma casa); agrupamentos com frequência acima da
                    média; rotas distintas no agrupamento de maior
                    frequência; maior número de rotas distintas num
                    agrupamento, com o posto e a frequência dele
    pontos_afericao total e contagem por formulário e por categoria

CAMADAS (camadas_internas_<slug>.gpkg, EPSG:5880; só as não vazias; colunas
numéricas, lógicas e de texto)
    acts, atrativos (com ord, rotulo e principal), pontos_afericao (com
    numero), trajetos, clusters, envoltoria_acts, centro_acts

MÉTODO
    Distâncias e áreas em SIRGAS 2000 / Brazil Polyconic (EPSG:5880).
    ACTs: CNPJs georreferenciados cujo município, normalizado por
        comum.normalizar_municipio, é o do estudo; registros sem coordenada
        saem; ficam só os que caem dentro do polígono municipal (IBGE 2025),
        porque o geocodificador erra parte dos endereços.
    Atrativos: camada 4_atrativos_turisticos do município. As correções de
        coordenada de correcoes_atrativos.json ("corrigir") são aplicadas por
        ID_ATRATIV, sem alterar a camada de origem. Ficam os atrativos dentro
        do município (com TOLERANCIA_TERRITORIO_M), os que estão fora do
        Brasil a até EXTERIOR_MAX_M do território municipal e os aceitos
        explicitamente ("aceitos_fora_do_territorio"); saem os listados em
        "excluir" e os demais fora do território, que são relatados.
        Hierarquia: atrativos_p4.ranquear (coluna ord: 1 a 5 pela tabela de
        relevância, 99 os demais).
    Centro: ponto de convergência dos trajetos modelados
        (fluxos_p4.centro_da_modelagem); sem trajetos, o centroide da
        envoltória convexa das ACTs.
    Trajetos: fluxos_p4.rotas, sem as rotas cujo atrativo de destino foi
        corrigido ou excluído (a rota modelada leva ao lugar errado).
    Sobreposição: fluxos_p4.clusters; as rotas fora do cálculo deixam de
        contar nas rotas distintas, e os agrupamentos e as frequências ficam
        como na seleção dos pontos.
    Pontos de aferição: camada consolidada, filtrada pelo município (campo
        cidade), ordenada pelo número do ponto; nome_ponto passa a ser o
        rótulo da síntese de campo, quando existe.

ENTRADAS (relativas a P4_DADOS)
    Levantamentos e Análises/Produto 4/06_Dados_Processados_Pipeline/
        CNPJs_e_Atrativos_Clusters/z_final_geocoded/cnpjs_georreferenciados.csv
            CNPJs das ACTs geocodificados (nome_municipio, latitude,
            longitude)
        CNPJs_e_Atrativos_Clusters/camadas_qgis/4_atrativos_turisticos.geojson
            atrativos (MUNICIPIO, LATITUDE, LONGITUDE, ID_ATRATIV, NOME,
            RANK_PROD4)
    Levantamentos e Análises/Produto 4/03_Pesquisa_de_Campo_Primaria/
        03_Pontos_Afericao/vetores_gis/pontos_afericao_consolidados.geojson
            pontos de aferição (cidade, ordem, nome_ponto, rotulo,
            formulario, categoria)
    Entregas/Produto 4/produção/Caderno de informações por município/
        02_Dados_Municipais/atrativos/correcoes_atrativos.json  (opcional)
            correções de coordenada, exclusões e exceções, com a fonte
    Malha municipal: bases_p4.municipios (IBGE 2025).
    Módulos: fluxos_p4 (trajetos, centro e agrupamentos, a partir de
    tomtom_routes.csv da seleção dos pontos) e atrativos_p4 (hierarquia, a
    partir de Atrativos_Relevantes_Por_Cidade.md).

SAÍDAS
    Entregas/Produto 4/produção/Caderno de informações por município/
        02_Dados_Municipais/<slug>/metricas_deslocamento_<slug>.json
        02_Dados_Municipais/<slug>/camadas_internas_<slug>.gpkg

COMO EXECUTAR
    python deslocamento_interno_p4.py 01_Foz_do_Iguacu_PR
    python deslocamento_interno_p4.py 02_Medianeira_PR 06_Guaira_PR

    O argumento é o slug de comum.MUNICIPIOS (um ou mais).

ORDEM
    Depende da seleção dos pontos (tomtom_routes.csv) e da camada consolidada
    de pontos já corrigida e nomeada (18_corrigir_camada_pontos.py,
    31_nomes_oficiais_pontos.py). As saídas são lidas por
    indicadores_campo_p4 (camada pontos_afericao) e por
    indicadores_municipais_p4 (atrativos, ACTs, trajetos e sobreposição).
================================================================================
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).parent))
import atrativos_p4 as ap                                        # noqa: E402
import bases_p4 as bp                                            # noqa: E402
import fluxos_p4 as fx                                           # noqa: E402
from comum import (ACERVO, CAMADAS_QGIS, CAMPO, CRS_DADOS,       # noqa: E402
                   CRS_MAPA, DIR_DADOS, MUNICIPIOS, POR_SLUG,
                   normalizar_municipio)

CNPJS = (ACERVO / "06_Dados_Processados_Pipeline" /
         "CNPJs_e_Atrativos_Clusters" / "z_final_geocoded" /
         "cnpjs_georreferenciados.csv")
PONTOS = (CAMPO / "03_Pontos_Afericao" / "vetores_gis" /
          "pontos_afericao_consolidados.geojson")
CORRECOES = DIR_DADOS / "atrativos" / "correcoes_atrativos.json"

# ══════════════════════════════════════════════════════════════════════════════
# PARÂMETROS
# ══════════════════════════════════════════════════════════════════════════════
TOLERANCIA_TERRITORIO_M = 500    # atrativo no limite municipal ainda conta
EXTERIOR_MAX_M = 30000           # atrativo do outro lado da fronteira
RAIO_CURTO_KM, RAIO_LONGO_KM = 2, 5


# ══════════════════════════════════════════════════════════════════════════════
# LEITURA
# ══════════════════════════════════════════════════════════════════════════════
def camada(nome: str, m) -> gpd.GeoDataFrame:
    """Uma das camadas da seleção dos pontos, recortada ao município."""
    g = json.loads((CAMADAS_QGIS / f"{nome}.geojson").read_text("utf-8"))
    linhas = [f["properties"] for f in g["features"]
              if normalizar_municipio(f["properties"].get("MUNICIPIO"))
              and normalizar_municipio(
                  f["properties"]["MUNICIPIO"]).codigo_ibge == m.codigo_ibge]
    if not linhas:
        return gpd.GeoDataFrame()
    d = pd.DataFrame(linhas)
    return gpd.GeoDataFrame(
        d, geometry=[Point(xy) for xy in zip(d.LONGITUDE, d.LATITUDE)],
        crs=CRS_DADOS).to_crs(CRS_MAPA)


def acts_do_municipio(m, territorio) -> gpd.GeoDataFrame:
    """CNPJs das ACTs do município que caem dentro do território."""
    cnpj = pd.read_csv(CNPJS, sep=";", encoding="utf-8-sig",
                       on_bad_lines="skip", engine="python")
    cnpj["lat"] = pd.to_numeric(cnpj.latitude, errors="coerce")
    cnpj["lon"] = pd.to_numeric(cnpj.longitude, errors="coerce")
    cnpj = cnpj[cnpj.nome_municipio.map(
        lambda v: (normalizar_municipio(v).codigo_ibge
                   if normalizar_municipio(v) else None) == m.codigo_ibge)]
    cnpj = cnpj.dropna(subset=["lat", "lon"])
    acts = gpd.GeoDataFrame(
        cnpj, geometry=[Point(xy) for xy in zip(cnpj.lon, cnpj.lat)],
        crs=CRS_DADOS).to_crs(CRS_MAPA)
    return acts[acts.within(territorio)]


def atrativos_do_municipio(m, territorio, mun: gpd.GeoDataFrame):
    """(atrativos mantidos, corrigidos, excluídos)."""
    atrativos = camada("4_atrativos_turisticos", m)
    corr = (json.loads(CORRECOES.read_text("utf-8"))
            if CORRECOES.exists() else {})
    corrigidos, excluidos = [], []
    if not len(atrativos):
        return atrativos, corrigidos, excluidos
    ids = pd.to_numeric(atrativos.ID_ATRATIV, errors="coerce")
    for c in corr.get("corrigir", []):
        sel = ids == c["id"]
        if sel.any():
            p = gpd.GeoSeries([Point(c["lon"], c["lat"])], crs=CRS_DADOS
                              ).to_crs(CRS_MAPA).iloc[0]
            atrativos.loc[sel, "geometry"] = p
            atrativos.loc[sel, ["LATITUDE", "LONGITUDE"]] = [c["lat"], c["lon"]]
            corrigidos.append({"id": c["id"], "nome": c["nome"],
                               "fonte": c["fonte"]})
            print(f"   atrativo corrigido: {c['nome']} ({c['fonte'][:60]}…)")
    excl = {c["id"]: c["motivo"] for c in corr.get("excluir", [])}
    aceitos = {c["id"] for c in corr.get("aceitos_fora_do_territorio", [])}
    dentro = atrativos.within(territorio.buffer(TOLERANCIA_TERRITORIO_M))
    j = gpd.sjoin(atrativos[["geometry"]], mun[["geometry"]], how="left",
                  predicate="within")
    no_brasil = j.groupby(level=0).index_right.apply(
        lambda v: v.notna().any()).reindex(atrativos.index, fill_value=False)
    exterior_perto = ~no_brasil & (atrativos.distance(territorio)
                                   <= EXTERIOR_MAX_M)
    manter = ((dentro | exterior_perto | ids.isin(aceitos))
              & ~ids.isin(list(excl)))
    for i in atrativos.index[~manter]:
        r = atrativos.loc[i]
        motivo = excl.get(int(ids[i]) if pd.notna(ids[i]) else None,
                          "fora do território, sem correção nem exceção "
                          "registrada")
        excluidos.append({"id": None if pd.isna(ids[i]) else int(ids[i]),
                          "nome": str(r.NOME), "motivo": motivo})
        print(f"   atrativo fora do cálculo: {r.NOME} ({motivo[:70]})")
    return atrativos[manter].copy(), corrigidos, excluidos


def pontos_de_afericao(m) -> gpd.GeoDataFrame:
    """Pontos aferidos no município, em ordem numérica ("Ponto #10" depois
    de "Ponto #9")."""
    cons = gpd.read_file(PONTOS)
    pts = cons[cons.cidade == m.nome].to_crs(CRS_MAPA).copy()
    pts["numero"] = pts.ordem.astype(str).str.extract(r"(\d+)").astype(int)
    # nome da síntese de campo, com o qualificador da área de análise onde o
    # nome se repete no município (31_nomes_oficiais_pontos.py)
    if "rotulo" in pts.columns:
        pts["nome_ponto"] = pts.rotulo.fillna(pts.nome_ponto)
    pts["nome_ponto"] = (pts.nome_ponto.astype(str)
                         .str.replace(r"\s+", " ", regex=True).str.strip())
    return pts.sort_values("numero")


# ══════════════════════════════════════════════════════════════════════════════
# CÁLCULO
# ══════════════════════════════════════════════════════════════════════════════
def deslocamento(m, mun: gpd.GeoDataFrame | None = None) -> dict:
    """Camadas e elementos do deslocamento interno; nada é gravado."""
    mun = bp.municipios() if mun is None else mun
    alvo = mun[mun.CD_MUN == m.codigo_ibge]
    territorio = alvo.geometry.iloc[0]

    acts = acts_do_municipio(m, territorio)
    atrativos, corrigidos, excluidos = atrativos_do_municipio(
        m, territorio, mun)
    pts = pontos_de_afericao(m)
    print(f"{m.nome_uf}: {len(acts)} ACTs · {len(atrativos)} atrativos · "
          f"{len(pts)} pontos de aferição")

    # Centro: lido do ponto em que os trajetos da seleção convergem, e não
    # recalculado, para que toda medida parta da mesma origem da modelagem.
    envoltoria = acts.geometry.union_all().convex_hull if len(acts) else None
    centro = fx.centro_da_modelagem(m.nome)
    if centro is None and envoltoria is not None:
        centro = envoltoria.centroid

    tabela_relevancia = []
    if len(atrativos):
        atrativos, tabela_relevancia = ap.ranquear(atrativos, m.nome)

    # A rota modelada até um atrativo mal localizado vai para o lugar
    # errado: saem as rotas dos atrativos corrigidos ou excluídos.
    trajetos = fx.rotas(m.nome)
    rotas_fora: set = set()
    rota_errada = ({c["nome"] for c in corrigidos}
                   | {c["nome"] for c in excluidos})
    if len(trajetos) and rota_errada:
        fora = trajetos.atrativo.astype(str).isin(rota_errada)
        for n in trajetos[fora].atrativo:
            print(f"   trajeto fora do cálculo (destino mal localizado): {n}")
        rotas_fora = set(trajetos[fora].id)
        trajetos = trajetos[~fora].copy()

    # Duas medidas que não medem a mesma coisa: `freq` é a contagem de
    # vértices das rotas no agrupamento de 100 m (o índice usado na seleção
    # dos pontos); `rotas_distintas` é quantas rotas passam ali.
    clusters = fx.clusters(m.nome, excluir_ids=rotas_fora)

    return {"acts": acts, "atrativos": atrativos, "pontos": pts,
            "envoltoria": envoltoria, "centro": centro,
            "tabela_relevancia": tabela_relevancia,
            "corrigidos": corrigidos, "excluidos": excluidos,
            "trajetos": trajetos, "rotas_fora": rotas_fora,
            "clusters": clusters}


def _so_atributos(gdf) -> gpd.GeoDataFrame:
    """Geometria e colunas numéricas, lógicas e de texto."""
    g = gdf.copy()
    return g[[c for c in g.columns if c == "geometry"
              or g[c].dtype.kind in "ifbOU"]]


def camadas(res: dict) -> dict:
    """{nome da camada: GeoDataFrame}, só as não vazias, em EPSG:5880."""
    saida: dict = {}
    for nome, gdf in (("acts", res["acts"]), ("atrativos", res["atrativos"]),
                      ("pontos_afericao", res["pontos"]),
                      ("trajetos", res["trajetos"]),
                      ("clusters", res["clusters"])):
        if gdf is not None and len(gdf):
            saida[nome] = _so_atributos(gdf)
    if res["envoltoria"] is not None:
        saida["envoltoria_acts"] = _so_atributos(gpd.GeoDataFrame(
            {"nome": ["envoltória das ACTs"]}, geometry=[res["envoltoria"]],
            crs=CRS_MAPA))
    if res["centro"] is not None:
        saida["centro_acts"] = _so_atributos(gpd.GeoDataFrame(
            {"nome": ["centro da modelagem"]}, geometry=[res["centro"]],
            crs=CRS_MAPA))
    return saida


def metricas(m, res: dict) -> dict:
    """Medidas do deslocamento interno (ver cabeçalho)."""
    acts, centro, envoltoria = res["acts"], res["centro"], res["envoltoria"]
    atrativos, trajetos, clusters = (res["atrativos"], res["trajetos"],
                                     res["clusters"])
    pts = res["pontos"]
    met: dict = {"municipio": m.nome_uf, "codigo_ibge": m.codigo_ibge}

    if len(acts):
        d_centro = acts.geometry.distance(centro) / 1000.0
        met["acts"] = {
            "total": int(len(acts)),
            "envoltoria_km2": round(envoltoria.area / 1e6, 1),
            "raio_medio_km": round(float(d_centro.mean()), 1),
            "raio_mediano_km": round(float(d_centro.median()), 1),
            "raio_max_km": round(float(d_centro.max()), 1),
            "dentro_de_2km_pct": round(float(
                (d_centro <= RAIO_CURTO_KM).mean() * 100), 1),
            "dentro_de_5km_pct": round(float(
                (d_centro <= RAIO_LONGO_KM).mean() * 100), 1),
        }
        cen = gpd.GeoSeries([centro], crs=CRS_MAPA).to_crs(CRS_DADOS).iloc[0]
        met["acts"]["centro_lat"] = round(cen.y, 6)
        met["acts"]["centro_lon"] = round(cen.x, 6)

    # extensão da rota mais curta até cada atrativo, onde a modelagem a traçou
    rota_km = ({str(k): round(float(v), 1) for k, v in trajetos.groupby(
        trajetos.atrativo.astype(str)).extensao_km.min().items()}
        if len(trajetos) and "extensao_km" in trajetos else {})
    if len(atrativos):
        at = atrativos.copy()
        at["d_km"] = (at.geometry.distance(centro) / 1000.0
                      if centro is not None else np.nan)
        met["atrativos"] = {
            "total": int(len(at)),
            "ranqueados": int(at[at.ord < 99].ord.nunique()),
            "distancia_media_km": round(float(at.d_km.mean()), 1),
            "distancia_max_km": round(float(at.d_km.max()), 1),
            "principais": [{"rank": int(g.ord), "nome": str(g.rotulo),
                            "distancia_km": round(float(g.d_km), 1),
                            "rota_km": rota_km.get(str(g.NOME))}
                           for g in at[at.principal]
                           .sort_values("ord").itertuples()],
            "tabela_relevancia": res["tabela_relevancia"],
            "corrigidos": res["corrigidos"],
            "excluidos": res["excluidos"],
        }

    if len(trajetos):
        comp = trajetos.extensao_km.tolist()
        met["trajetos"] = {
            "total": int(len(trajetos)),
            "extensao_media_km": round(float(np.mean(comp)), 1),
            "extensao_mediana_km": round(float(np.median(comp)), 1),
            "extensao_max_km": round(float(np.max(comp)), 1),
            "extensao_somada_km": round(float(np.sum(comp)), 1),
        }

    if len(clusters):
        top_freq = clusters.nlargest(1, "freq").iloc[0]
        top_rotas = clusters.nlargest(1, "rotas_distintas").iloc[0]
        met["sobreposicao"] = {
            "raio_agrupamento_m": fx.EPS_METROS,
            "total": int(len(clusters)),
            "vertices": int(len(fx._vertices(m.nome))),
            "freq_max": int(top_freq.freq),
            "freq_media": round(float(clusters.freq.mean()), 1),
            "acima_da_media": int((clusters.freq > clusters.freq.mean()).sum()),
            "rotas_no_maior_freq": int(top_freq.rotas_distintas),
            "rotas_distintas_max": int(top_rotas.rotas_distintas),
            "posto_do_mais_percorrido": int(top_rotas["rank"]),
            "freq_do_mais_percorrido": int(top_rotas.freq),
        }

    if len(pts):
        met["pontos_afericao"] = {
            "total": int(len(pts)),
            "por_formulario": {str(k): int(v) for k, v in
                               pts.formulario.value_counts().items()},
            "por_categoria": {str(k): int(v) for k, v in
                              pts.categoria.value_counts().items()},
        }
    return met


# ══════════════════════════════════════════════════════════════════════════════
# EXECUÇÃO
# ══════════════════════════════════════════════════════════════════════════════
def arquivos(m) -> tuple[Path, Path]:
    pasta = DIR_DADOS / m.slug
    return (pasta / f"metricas_deslocamento_{m.slug}.json",
            pasta / f"camadas_internas_{m.slug}.gpkg")


def gravar(m, res: dict) -> list[Path]:
    """Grava as camadas (GeoPackage, uma camada por elemento) e as medidas."""
    arq_met, arq_cam = arquivos(m)
    arq_met.parent.mkdir(parents=True, exist_ok=True)
    cam = camadas(res)
    for nome, g in cam.items():
        g.to_file(arq_cam, layer=nome, driver="GPKG")
    if cam:
        print(f"camadas gravadas: {', '.join(cam)} -> {arq_cam.name}")
    arq_met.write_text(json.dumps(metricas(m, res), ensure_ascii=False,
                                  indent=2), "utf-8")
    return [arq_met] + ([arq_cam] if cam else [])


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
        res = deslocamento(m, mun)
        for p in gravar(m, res):
            print("   " + str(p))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
