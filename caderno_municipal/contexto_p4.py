# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMAÇÕES POR MUNICÍPIO | PRODUTO 4
CONTEXTO DE ACESSO: RODOVIAS, TRÁFEGO, ÁREAS PROTEGIDAS, ÔNIBUS, AÉREO, NÁUTICA
================================================================================
Calcula, por município e por tema, as medidas de contexto do acesso ao
município.

TEMAS E MEDIDAS (metricas_contexto_<slug>.json)
    rodovias
        rodovias    rodovias federais que cruzam o território, sem os trechos
                    planejados (superfície PLA): extensão no território (km,
                    uma casa) e superfícies; rodovias estaduais (UF-código) e
                    extensão estadual somada no território (km, uma casa);
                    pontes internacionais e passagens de fronteira sem ponte;
                    polo regional de referência
        trafego     trechos federais do município com contagem do PNCT:
                    veículos e veículos comerciais por dia (inteiros) e
                    classe, do maior para o menor volume; maior volume no
                    recorte; acessos que a base VDM do DNIT associa ao
                    município; ferrovia no recorte (km e km interrompidos,
                    uma casa; linhas) e se alcança o território
    protegidas      unidades de conservação federais que tocam o território,
                    com a categoria e a parcela do território (%, uma casa);
                    terras indígenas no recorte, com o município declarado e
                    se tocam o território; parcela do território na faixa de
                    proteção do reservatório de Itaipu (%, uma casa); sítios
                    arqueológicos no território
    onibus
        onibus_periodo   meses da bilhetagem
        onibus      bilhetagem interestadual (ANTT): passagens somadas nos
                    dois sentidos, ligações, saídas e chegadas, os dez
                    destinos de mais passagens (participação, uma casa, e
                    tarifa média ponderada pelos bilhetes pagos, duas
                    casas), participação dos dez, participação por UF e das
                    gratuidades; sem passagens, participações vazias
        onibus_clickbus  amostra da oferta (linhas, em ordem de distância),
                    registro do terminal, destinos internacionais em
                    destaque e trechos de chegada a partir dos polos
                    emissores (passageiros da ANTT só nos interestaduais)
    aereo           só municípios com aeródromo: rotas regulares com
                    passageiros no ano, passageiros somados, rotas da malha
                    sem passageiro, rotas com origem fora do Brasil e as oito
                    principais, com a participação (%, uma casa)
    nautica         só municípios com água navegável: rotas propostas que
                    tocam o entorno do município, pontos nomeados (prainhas,
                    balneários, portos de lazer), travessias, portos e
                    hidrovias da ANTAQ no entorno

MÉTODO
    Extensões e áreas em SIRGAS 2000 / Brazil Polyconic (EPSG:5880).
    Território: polígono municipal do IBGE (2025). Entorno náutico: o
        território ampliado de ENTORNO_NAUTICO_M.
    Recorte: o maior volume de tráfego, a ferrovia e as terras indígenas são
        medidos num recorte em torno do município, e não só no território.
        O recorte é o envelope de elementos de referência, ampliado pela
        folga (fração da largura e da altura, em cada lado) e então
        alargado no lado menor, de forma centrada, até a proporção
        largura/altura PROPORCAO_RECORTE.
            rodovias     o território, as cidades estrangeiras vizinhas
                         (VIZINHAS_EXTERIOR) e a sede do polo regional
                         (POLO_REGIONAL), folga FOLGA_RODOVIAS
            protegidas   o território, folga FOLGA_PROTEGIDAS
    Passagens de fronteira: fim de trecho do SNV no território que termina
        na fronteira (Local_Fim). O nome da ponte vem do texto do trecho
        (Amizade, Tancredo Neves, Integração); sem ele, "Ponte
        internacional". Nos municípios de TRAVESSIA_SEM_PONTE o fim do
        trecho não é ponte e entra o tipo de passagem.
    Tráfego: volume médio diário anual do Plano Nacional de Contagem de
        Tráfego (DNIT, 2025), ligado ao SNV pelo código do trecho
        (trafego_p4). Trecho sem contagem significa "não medido".
    Bilhetagem: passagens com origem ou destino no município ("Nome/UF"),
        agregadas pelo outro extremo; destinos sem sede localizável na malha
        municipal ficam fora dos dez principais, mas contam nas ligações.
        Participações sobre o total de passagens dos dois sentidos.
    Malha aérea: rotas regulares com origem ou destino no município; os
        aeroportos de NOME_AEROPORTO entram com o nome do aeroporto onde o do
        município é ambíguo.
    Náutica: as rotas do acervo Ocean Eyes são proposta de roteirização, não
        navegação existente; entram só na contagem de rotas propostas.
    Temas pedidos são recalculados; os demais mantêm o que já estava
        gravado no arquivo do município.

ENTRADAS (relativas a P4_DADOS)
    Malhas: bases_p4.municipios (IBGE 2025), bases_p4.rodovias (SNV e CIDE,
    DNIT), bases_p4.reservatorio_itaipu (Zoneamento_FP_Reserv.shp, feições
    do tipo "Áreas Protegidas").
    Levantamentos e Análises/Produto 4/01_Bases_Secundarias_Oficiais/Shapes/
        vw_icmbio_unid_conserv.zip, vw_funai_terras_indigenas.zip,
        vw_iphan_sitios_arq.zip, vw_antaq_travessias.zip,
        vw_antaq_portos.zip, vw_antaq_vias_navegaveis.zip
    Levantamentos e Análises/Produto 4/08_Infraestrutura_e_Turismo_Nautico/
        01_Vetores_e_Rotas_Nauticas/rotas_ocean_eyes.geojson,
        catalogo_waypoints_unicos.csv
    Entregas/Produto 4/produção/08_transporte_coletivo_rodoviarias_clickbus/
        consolidado_final_01_09_2026.csv  (bilhetagem ANTT)
        amostra_rotas_oferta_onibus_clickbus_faixa_fronteira.csv
        tabela_diferenciacao_rotas_terminais_fronteira.csv
        tabela_trechos_inbound_portas_entrada_onibus.csv
    Entregas/Produto 4/produção/09_aviacao_rotas_e_aeroportos_anac/
        malha_rotas_aereas_regulares_anac.geojson
    Módulo trafego_p4: contagens do PNCT, acessos da base VDM e malha
    ferroviária (vw_dif_ferrovias.zip).

SAÍDAS
    Entregas/Produto 4/produção/Caderno de informações por município/
        02_Dados_Municipais/<slug>/metricas_contexto_<slug>.json

COMO EXECUTAR
    python contexto_p4.py 01_Foz_do_Iguacu_PR
    python contexto_p4.py 01_Foz_do_Iguacu_PR 10_Corumba_MS rodovias aereo

    Slugs de comum.MUNICIPIOS (um ou mais) e, opcionalmente, os temas
    (rodovias, protegidas, onibus, aereo, nautica); sem tema, todos.

ORDEM
    Depende só das bases listadas. A saída é lida por indicadores_municipais_p4
    (rodovias, tráfego, ônibus, aéreo, náutica) e por indicadores_campo_p4
    (rotas aéreas internacionais).
================================================================================
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box

sys.path.insert(0, str(Path(__file__).parent))
import bases_p4 as bp                                            # noqa: E402
import trafego_p4 as trf                                         # noqa: E402
from comum import (ACERVO, CRS_DADOS, CRS_MAPA, DIR_DADOS,       # noqa: E402
                   MUNICIPIOS, POR_SLUG, PRODUCAO)

SH = ACERVO / "01_Bases_Secundarias_Oficiais" / "Shapes"
NAUT = ACERVO / "08_Infraestrutura_e_Turismo_Nautico" / "01_Vetores_e_Rotas_Nauticas"
CLICKBUS = PRODUCAO / "08_transporte_coletivo_rodoviarias_clickbus"
ANAC = (PRODUCAO / "09_aviacao_rotas_e_aeroportos_anac" /
        "malha_rotas_aereas_regulares_anac.geojson")

TEMAS = ("rodovias", "protegidas", "onibus", "aereo", "nautica")

# ══════════════════════════════════════════════════════════════════════════════
# PARÂMETROS
# ══════════════════════════════════════════════════════════════════════════════
PROPORCAO_RECORTE = 20.0 / 21.0       # largura / altura do recorte
FOLGA_RODOVIAS = 0.12
FOLGA_PROTEGIDAS = 0.35
ENTORNO_NAUTICO_M = 3000
DESTINOS_PRINCIPAIS = 10              # bilhetagem: destinos detalhados
ROTAS_AEREAS_PRINCIPAIS = 8

# Cidades do outro lado da fronteira (lon, lat), sem camada oficial no
# acervo: entram no recorte das rodovias.
VIZINHAS_EXTERIOR = {
    "01_Foz_do_Iguacu_PR": {
        "Ciudad del Este (PY)": (-54.6110, -25.5097),
        "Puerto Iguazú (AR)": (-54.5736, -25.5991),
    },
}
# Polo regional para onde convergem as rodovias do município (nome, UF)
POLO_REGIONAL = {
    "01_Foz_do_Iguacu_PR": ("Cascavel", "PR"),
}
# Onde o fim do trecho do SNV na fronteira não é ponte (OpenStreetMap,
# conferido em 05/10/2026, cruzando as pontes com o limite internacional).
TRAVESSIA_SEM_PONTE = {"07_Mundo_Novo_MS": "fronteira seca",
                       "08_Ponta_Pora_MS": "fronteira seca",
                       "09_Porto_Murtinho_MS": "travessia fluvial"}
# A malha aérea nomeia pelo município; onde há ambiguidade, o aeroporto
# entra no nome.
NOME_AEROPORTO = {"SBSP": "São Paulo/Congonhas",
                  "SBGL": "Rio de Janeiro/Galeão",
                  "SBRJ": "Rio de Janeiro/Santos Dumont",
                  "SBCT": "Curitiba", "SAEZ": "Buenos Aires/Ezeiza",
                  "SABE": "Buenos Aires/Aeroparque",
                  "SBCF": "Belo Horizonte/Confins"}
MESES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
         "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}


# ══════════════════════════════════════════════════════════════════════════════
# AUXILIARES
# ══════════════════════════════════════════════════════════════════════════════
def zipshp(nome: str) -> gpd.GeoDataFrame:
    return gpd.read_file(f"zip://{SH / nome}").to_crs(CRS_MAPA)


def _csv(caminho: Path) -> pd.DataFrame:
    """CSV com separador detectado e sem o BOM no nome das colunas."""
    d = pd.read_csv(caminho, sep=None, engine="python")
    d.columns = [c.lstrip("﻿") for c in d.columns]
    return d


def envelope(gdf: gpd.GeoDataFrame, folga: float, proporcao=None):
    """(x0, x1, y0, y1): envelope com folga e, se pedida, a proporção
    largura/altura, alargando o lado menor de forma centrada."""
    x0, y0, x1, y1 = gdf.total_bounds
    dx, dy = x1 - x0, y1 - y0
    x0, x1 = x0 - dx * folga, x1 + dx * folga
    y0, y1 = y0 - dy * folga, y1 + dy * folga
    if proporcao:
        dx, dy = x1 - x0, y1 - y0
        if dx / dy < proporcao:
            extra = (proporcao * dy - dx) / 2
            x0, x1 = x0 - extra, x1 + extra
        else:
            extra = (dx / proporcao - dy) / 2
            y0, y1 = y0 - extra, y1 + extra
    return x0, x1, y0, y1


def recorte(gdf: gpd.GeoDataFrame, folga: float):
    """Polígono do recorte em torno dos elementos de referência."""
    e = envelope(gdf, folga, PROPORCAO_RECORTE)
    return box(e[0], e[2], e[1], e[3])


def sede(mun: gpd.GeoDataFrame, nome_mun: str, uf: str | None = None):
    """Ponto interior do município pelo nome (malha IBGE)."""
    s = mun[mun.NM_MUN.str.lower() == nome_mun.lower()]
    if uf is not None and "SIGLA_UF" in mun.columns and len(s) > 1:
        s = s[s.SIGLA_UF == uf]
    return s.geometry.iloc[0].representative_point() if len(s) else None


def chave(s: str) -> str:
    t = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in t if not unicodedata.combining(c)).lower().strip()


# ══════════════════════════════════════════════════════════════════════════════
# RODOVIAS E TRÁFEGO
# ══════════════════════════════════════════════════════════════════════════════
def rodovias(m, mun: gpd.GeoDataFrame, geom) -> dict:
    """{"trafego": ..., "rodovias": ...}."""
    fed = bp.rodovias("federal")
    fed = fed[~fed.Superficie.isin(["PLA"])]
    est = bp.rodovias("cide")
    est = est[~est.Superficie.isin(["PLA"])]
    brs = sorted({int(b) for b in fed[fed.intersects(geom)].Codigo_BR.dropna()
                  if str(b).isdigit()})

    exterior = [gpd.GeoSeries([Point(v[0], v[1])], crs=CRS_DADOS)
                .to_crs(CRS_MAPA).iloc[0]
                for v in VIZINHAS_EXTERIOR.get(m.slug, {}).values()]
    polo = POLO_REGIONAL.get(m.slug)
    ancoras = [geom] + exterior + ([sede(mun, *polo)] if polo else [])
    caixa = recorte(gpd.GeoDataFrame(geometry=ancoras, crs=CRS_MAPA),
                    FOLGA_RODOVIAS)

    # maior volume contado entre os trechos federais do recorte
    f_vis = fed[fed.intersects(caixa)]
    cont = trf.contagens()
    f_vis = f_vis.assign(
        vmda_pnct=[cont.get(str(c), {}).get("vmda", 0.0)
                   for c in f_vis.Codigo_SNV])
    com_cont = f_vis[f_vis.vmda_pnct > 0]
    vmax = float(com_cont.vmda_pnct.max()) if len(com_cont) else 0.0

    # ferrovia: na faixa é malha de carga, e parte está interrompida
    fer = trf.ferrovias(CRS_MAPA)
    fer_vis = fer[fer.intersects(caixa)] if fer is not None else None

    # passagens de fronteira: fim do trecho SNV que termina na fronteira
    pontes, passagens = [], []
    for r in fed[fed.intersects(geom)].itertuples():
        txt = f"{r.Local_Inic} {r.Local_Fim}".upper()
        if "FRONT" not in str(r.Local_Fim).upper():
            continue
        nome_p = ("Ponte da Amizade" if "AMIZADE" in txt else
                  "Ponte Tancredo Neves" if "TANCREDO" in txt else
                  "Ponte da Integração" if "2" in txt and "PONTE" in txt else
                  "Ponte internacional")
        if nome_p == "Ponte internacional" and m.slug in TRAVESSIA_SEM_PONTE:
            tipo = TRAVESSIA_SEM_PONTE[m.slug]
            if tipo not in passagens:
                passagens.append(tipo)
        elif nome_p not in pontes:
            pontes.append(nome_p)

    no_mun = fed[fed.intersects(geom)]
    tr_mun = sorted(
        ({"br": int(r.Codigo_BR) if str(r.Codigo_BR).isdigit() else None,
          "trecho": f"{r.Local_Inic} → {r.Local_Fim}",
          "veiculos_dia": round(cont[str(r.Codigo_SNV)]["vmda"]),
          "comerciais_dia": round(cont[str(r.Codigo_SNV)]["comercial"]),
          "classe": cont[str(r.Codigo_SNV)]["classe"]}
         for r in no_mun.itertuples() if str(r.Codigo_SNV) in cont),
        key=lambda x: -x["veiculos_dia"])
    trafego = {
        "trechos_no_municipio": tr_mun,
        "maior_volume_no_recorte": round(vmax),
        "portas_dnit": trf.portas(m.nome),
        "ferrovia_km_no_recorte": (
            round(float(fer_vis.length.sum()) / 1000, 1)
            if fer_vis is not None and len(fer_vis) else 0),
        "ferrovia_interrompida_km": (
            round(float(fer_vis[fer_vis.interrompida].length.sum()) / 1000, 1)
            if fer_vis is not None and len(fer_vis) else 0),
        "ferrovia_alcanca_o_municipio": bool(
            fer is not None and len(fer[fer.intersects(geom)])),
        "ferrovia_linhas_no_recorte": (
            sorted({str(x) for x in fer_vis.Linha.dropna()})
            if fer_vis is not None and len(fer_vis) else []),
    }

    ext_mun = {}
    for b in brs:
        tr = fed[(fed.Codigo_BR.astype(str) == str(b)) & fed.intersects(geom)]
        ext_mun[f"BR-{b:03d}"] = {
            "km_no_municipio": round(float(tr.intersection(geom).length.sum()
                                           / 1000), 1),
            "superficies": sorted(tr.Superficie.dropna().unique().tolist()),
        }
    est_mun = est[est.intersects(geom)]
    rod = {
        "federais": ext_mun,
        "estaduais": sorted({f"{r.Unidade_Fe}-{r.Codigo_Rod}"
                             for r in est_mun.itertuples()
                             if str(r.Codigo_Rod).strip()}),
        "estaduais_km": round(float(est_mun.intersection(geom).length.sum()
                                    / 1000), 1),
        "pontes": pontes,
        "passagens_sem_ponte": passagens,
        "polo": polo[0] if polo else None,
    }
    return {"trafego": trafego, "rodovias": rod}


# ══════════════════════════════════════════════════════════════════════════════
# ÁREAS PROTEGIDAS
# ══════════════════════════════════════════════════════════════════════════════
def protegidas(alvo: gpd.GeoDataFrame, geom) -> dict:
    caixa = recorte(alvo, FOLGA_PROTEGIDAS)
    uc = zipshp("vw_icmbio_unid_conserv.zip")
    ti = zipshp("vw_funai_terras_indigenas.zip")
    sa = zipshp("vw_iphan_sitios_arq.zip")
    lago = bp.reservatorio_itaipu()
    fp_res = (lago[lago.tipo == "Áreas Protegidas"] if lago is not None
              else None)

    ti_v = ti[ti.intersects(caixa)]
    area_mun = geom.area
    uc_m = uc[uc.intersects(geom)]
    fp_m = (fp_res[fp_res.intersects(geom)] if fp_res is not None
            else gpd.GeoDataFrame())
    sa_m = sa[sa.intersects(geom)]
    return {"protegidas": {
        "ucs": [{"nome": str(r.Nome), "categoria": str(r.Categoria),
                 "pct_do_municipio": round(float(r.geometry.intersection(geom)
                                                 .area / area_mun * 100), 1)}
                for r in uc_m.itertuples()],
        "tis": [{"nome": str(r.Nome), "municipio": str(r.Municipio),
                 "no_municipio": bool(r.geometry.intersection(geom).area > 0)}
                for r in ti_v.itertuples()],
        "faixa_reservatorio_pct": (round(float(fp_m.intersection(geom).area.sum()
                                               / area_mun * 100), 1)
                                   if len(fp_m) else 0.0),
        "sitios_arqueologicos": int(len(sa_m)),
    }}


# ══════════════════════════════════════════════════════════════════════════════
# ÔNIBUS
# ══════════════════════════════════════════════════════════════════════════════
def onibus(m, mun: gpd.GeoDataFrame) -> dict:
    """{"onibus_periodo", "onibus", "onibus_clickbus"}."""
    b = _csv(CLICKBUS / "consolidado_final_01_09_2026.csv")
    alvo_txt = f"{m.nome}/{m.uf}"
    b["_o"], b["_d"] = (b.ponto_origem_viagem.astype(str),
                        b.ponto_destino_viagem.astype(str))
    sai = b[b._o == alvo_txt].assign(outro=lambda x: x._d, sentido="saída")
    che = b[b._d == alvo_txt].assign(outro=lambda x: x._o, sentido="chegada")
    fl = pd.concat([sai, che])
    fl = fl[fl.outro != alvo_txt]
    ag = (fl.groupby("outro")
          .agg(bilhetes=("quantidade_bilhetes", "sum"))
          .reset_index())
    pagos = fl[fl.media_valor_total > 0]
    tar = (pagos.assign(r=pagos.media_valor_total * pagos.quantidade_bilhetes)
           .groupby("outro").agg(r=("r", "sum"), q=("quantidade_bilhetes", "sum")))
    ag["tarifa_media"] = ag.outro.map((tar.r / tar.q).round(2))
    ag = ag.sort_values("bilhetes", ascending=False)

    # sede do outro extremo ("Nome/UF") na malha municipal
    nomes = mun.NM_MUN.map(chave)

    def ponto_de(txt):
        m_ = re.match(r"(.+)/(\w\w)$", str(txt))
        if not m_:
            return None
        nome, uf = m_.group(1).strip(), m_.group(2)
        s = mun[(nomes == chave(nome))]
        if "SIGLA_UF" in mun.columns:
            s = s[s.SIGLA_UF == uf]
        return s.geometry.iloc[0].representative_point() if len(s) else None

    ag["geom"] = ag.outro.map(ponto_de)
    sem_geo = ag[ag.geom.isna()]
    ag = ag[ag.geom.notna()]

    # oferta levantada na ClickBus (set/2026) e terminal
    am = _csv(CLICKBUS / "amostra_rotas_oferta_onibus_clickbus_faixa_fronteira.csv")
    am = am[(am.municipio_origem == m.nome) | (am.municipio_destino == m.nome)]
    am["outro"] = am.apply(lambda r: r.municipio_destino if r.municipio_origem
                           == m.nome else r.municipio_origem, axis=1)
    am["uf_outro"] = am.apply(lambda r: r.uf_destino if r.municipio_origem
                              == m.nome else r.uf_origem, axis=1)
    term = _csv(CLICKBUS / "tabela_diferenciacao_rotas_terminais_fronteira.csv")
    term = term[term.municipio == m.nome]
    intl = []
    if len(term):
        intl = [re.sub(r"\s*\(.*\)", "", x).strip() for x in
                str(term.destinos_internacionais_destaque.iloc[0]).split(",")]

    tot = int(fl.quantidade_bilhetes.sum())

    def _pct(x):
        """Sem linha interestadual regulada não há total: a participação não
        existe."""
        return None if not tot else round(float(x) / tot * 100, 1)

    meses = sorted(fl.mes_viagem.dropna().astype(str).unique(),
                   key=lambda m_: (MESES.get(m_[:3], 0), m_[-2:]))
    out = {"onibus_periodo": meses}
    out["onibus"] = {
        "fonte": "ANTT — bilhetagem do transporte rodoviário interestadual "
                 "de passageiros, 2025",
        "passagens_total": tot,
        "ligacoes": int(len(ag) + len(sem_geo)),
        "saidas": int(sai.quantidade_bilhetes.sum()),
        "chegadas": int(che.quantidade_bilhetes.sum()),
        "principais": [{"cidade": r.outro, "passagens": int(r.bilhetes),
                        "pct": _pct(r.bilhetes),
                        "tarifa_media": (None if pd.isna(r.tarifa_media)
                                         else float(r.tarifa_media))}
                       for r in ag.head(DESTINOS_PRINCIPAIS).itertuples()],
        "top10_pct": _pct(ag.head(DESTINOS_PRINCIPAIS).bilhetes.sum()),
        "pct_por_uf": {uf: _pct(v) for uf, v in
                       fl.groupby(fl.outro.astype(str).str[-2:])
                       .quantidade_bilhetes.sum()
                       .sort_values(ascending=False).items()},
        "pct_gratuidade": _pct(fl[fl.media_valor_total == 0]
                               .quantidade_bilhetes.sum()),
    }
    out["onibus_clickbus"] = {
        "fonte": "ClickBus, consulta de set/2026 (oferta); ANTT 2025 "
                 "(passageiros das linhas interestaduais)",
        "linhas": [{"cidade": r.outro, "uf": r.uf_outro,
                    "tipo": ("estadual" if r.uf_outro == m.uf
                             else "interestadual"),
                    "partidas_dia": int(r.partidas_diarias),
                    "duracao": str(r.duracao_viagem),
                    "distancia_km": int(r.distancia_km),
                    "classe": str(r.classe_servico),
                    "preco_total": float(r.preco_total_brl),
                    "viacao": str(r.viacao)}
                   for r in am.sort_values("distancia_km").itertuples()],
        "terminal": (term.iloc[0].drop(["lat", "lon"]).to_dict()
                     if len(term) else {}),
        "internacionais": intl,
    }
    # trechos de chegada desde os polos emissores: partidas, duração e preço
    # levantados na ClickBus, passageiros da ANTT
    inb = _csv(CLICKBUS / "tabela_trechos_inbound_portas_entrada_onibus.csv")
    inb = inb[inb.dest == alvo_txt]
    out["onibus_clickbus"]["chegadas"] = [
        {"cidade": str(r.orig).split("/")[0], "uf": str(r.orig)[-2:],
         "partidas_dia": int(r.freq), "duracao": str(r.dur),
         "distancia_km": int(r.dist), "preco_medio": float(r.preco),
         "viacoes": str(r.viacoes), "eixo": str(r.eixo),
         "passageiros_antt": (int(r.pax) if str(r.orig)[-2:] != m.uf
                              else None)}
        for r in inb.sort_values("dist").itertuples()]
    return out


# ══════════════════════════════════════════════════════════════════════════════
# MALHA AÉREA
# ══════════════════════════════════════════════════════════════════════════════
def aereo(m) -> dict:
    """{"aereo": ...}, ou vazio se nenhuma rota teve passageiro no ano."""
    rotas = gpd.read_file(ANAC)
    rm = rotas[rotas.dest_muni.astype(str).str.contains(m.nome) |
               rotas.orig_muni.astype(str).str.contains(m.nome)].copy()
    for lado in ("orig", "dest"):
        novo = rm[f"{lado}_icao"].map(NOME_AEROPORTO)
        rm[f"{lado}_muni"] = novo.fillna(rm[f"{lado}_muni"])
    sem_fluxo = rm[rm.pax_tot.fillna(0) <= 0].copy()
    rm = rm[rm.pax_tot.fillna(0) > 0].copy()
    if not len(rm):
        return {}
    rm = rm.sort_values("pax_tot", ascending=False)
    tot = float(rm.pax_tot.sum())
    return {"aereo": {
        "fonte": "ANAC — rotas regulares domésticas com destino ou "
                 "origem no município",
        "rotas": int(len(rm)), "passageiros": int(tot),
        "rotas_sem_fluxo": [str(r.orig_muni if m.nome not in
                                str(r.orig_muni) else r.dest_muni)
                            for r in sem_fluxo.itertuples()],
        "internacionais": [{"cidade": str(r.orig_muni),
                            "pais": str(r.orig_pais),
                            "passageiros": int(r.pax_tot)}
                           for r in rm.itertuples()
                           if str(r.orig_pais) != "BRA"],
        "principais": [{"cidade": str(r.orig_muni if m.nome not in
                                      str(r.orig_muni) else r.dest_muni),
                        "passageiros": int(r.pax_tot),
                        "pct": round(r.pax_tot / tot * 100, 1)}
                       for r in rm.head(ROTAS_AEREAS_PRINCIPAIS).itertuples()],
    }}


# ══════════════════════════════════════════════════════════════════════════════
# NÁUTICA
# ══════════════════════════════════════════════════════════════════════════════
def nautica(geom) -> dict:
    rotas_n = gpd.read_file(NAUT / "rotas_ocean_eyes.geojson").to_crs(CRS_MAPA)
    wps = _csv(NAUT / "catalogo_waypoints_unicos.csv")
    wps = gpd.GeoDataFrame(wps, geometry=[Point(xy) for xy in
                                          zip(wps.longitude_decimal,
                                              wps.latitude_decimal)],
                           crs=CRS_DADOS).to_crs(CRS_MAPA)
    trav = zipshp("vw_antaq_travessias.zip")
    portos = zipshp("vw_antaq_portos.zip")
    vias = zipshp("vw_antaq_vias_navegaveis.zip")

    entorno = geom.buffer(ENTORNO_NAUTICO_M)
    nomeados = wps[wps.descricao_principal.notna()]
    no_mun = nomeados[nomeados.intersects(entorno)]
    rotas_mun = rotas_n[rotas_n.intersects(entorno)]
    return {"nautica": {
        "rotas_propostas_que_tocam_o_municipio": int(len(rotas_mun)),
        "pontos_nomeados_no_municipio": sorted(
            {str(x).split(",")[0] for x in no_mun.descricao_principal}),
        "travessias": [str(t.Travessia) for t in
                       trav[trav.intersects(entorno)].itertuples()],
        "portos_antaq": [str(p.Nome) for p in
                         portos[portos.intersects(entorno)].itertuples()],
        "hidrovias": sorted({str(v.Nome) for v in
                             vias[vias.intersects(entorno)].itertuples()}),
    }}


# ══════════════════════════════════════════════════════════════════════════════
# CONJUNTO POR MUNICÍPIO
# ══════════════════════════════════════════════════════════════════════════════
def metricas_contexto(m, temas=TEMAS,
                      mun: gpd.GeoDataFrame | None = None) -> dict:
    """Medidas dos temas pedidos, na ordem dos temas. Aéreo só com
    aeródromo; náutica só com água navegável."""
    mun = bp.municipios() if mun is None else mun
    alvo = mun[mun.CD_MUN == m.codigo_ibge]
    geom = alvo.geometry.iloc[0]
    met: dict = {}
    if "rodovias" in temas:
        met.update(rodovias(m, mun, geom))
    if "protegidas" in temas:
        met.update(protegidas(alvo, geom))
    if "onibus" in temas:
        met.update(onibus(m, mun))
    if "aereo" in temas and m.tem_aerodromo:
        met.update(aereo(m))
    if "nautica" in temas and m.agua_navegavel:
        met.update(nautica(geom))
    return met


# ══════════════════════════════════════════════════════════════════════════════
# EXECUÇÃO
# ══════════════════════════════════════════════════════════════════════════════
def arquivo(m) -> Path:
    return DIR_DADOS / m.slug / f"metricas_contexto_{m.slug}.json"


def gravar(m, novos: dict) -> Path:
    """Atualiza o arquivo do município com os temas recalculados."""
    arq = arquivo(m)
    arq.parent.mkdir(parents=True, exist_ok=True)
    met = json.loads(arq.read_text("utf-8")) if arq.exists() else {}
    for k, v in novos.items():
        met[k] = v
    arq.write_text(json.dumps(met, ensure_ascii=False, indent=1, default=str),
                   "utf-8")
    return arq


def main(argv: list[str] | None = None) -> None:
    args = [a for a in (sys.argv[1:] if argv is None else argv)
            if not a.startswith("--")]
    slugs = [a for a in args if a not in TEMAS]
    temas = tuple(a for a in args if a in TEMAS) or TEMAS
    if not slugs:
        print("Informe o slug do município. Ex.: 01_Foz_do_Iguacu_PR")
        sys.exit(1)
    desconhecidos = [a for a in slugs if a not in POR_SLUG]
    if desconhecidos:
        print("Slug ou tema não reconhecido: " + ", ".join(desconhecidos))
        print("Municípios: " + ", ".join(m.slug for m in MUNICIPIOS))
        print("Temas: " + ", ".join(TEMAS))
        sys.exit(1)
    mun = bp.municipios()
    for slug in slugs:
        m = POR_SLUG[slug]
        print(f"\n{m.nome_uf}: {', '.join(temas)}")
        print("   " + str(gravar(m, metricas_contexto(m, temas, mun))))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
