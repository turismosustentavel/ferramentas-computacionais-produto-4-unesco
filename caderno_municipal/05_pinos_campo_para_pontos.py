# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
FASE 1c - PINOS DE CAMPO (GOOGLE MAPS) -> PONTOS DE AFERICAO
================================================================================
As listas compartilhadas do Google Maps feitas pela equipe em campo carregam
exatamente os rotulos usados nas fichas ("P1", "ponto 3", "rodoviaria"). Sao a
ponte que faltava entre o texto livre da ficha e o ponto mapeado.

Este script converte os pinos para coordenadas decimais e os liga a camada
consolidada (pontos_afericao_consolidados.geojson, 89 pontos com 'ordem',
'categoria' e 'formulario') por PROXIMIDADE - nao por nome. A geometria evita
todo o problema de vocabulario que trava o casamento textual.

SAIDA:
    02_Dados_Municipais/pinos_campo_para_pontos.xlsx
================================================================================
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).parent))
from comum import CAMPO, DIR_DADOS, parse_coordenadas  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CONSOLIDADO = (CAMPO / "03_Pontos_Afericao" / "vetores_gis" /
               "pontos_afericao_consolidados.geojson")

# ==============================================================================
# PINOS COLHIDOS DAS LISTAS COMPARTILHADAS DA EQUIPE DE CAMPO (22/09/2026)
# Formato: (cidade da lista, coordenada como exibida, rotulo de campo)
# ==============================================================================
PINOS: list[tuple[str, str, str]] = [
    # --- Corumba -------------------------------------------------------------
    ("Corumbá", "18°59'57.6\"S 57°39'42.6\"W", "P3"),
    ("Corumbá", "19°00'52.6\"S 57°38'34.0\"W", "P2"),
    ("Corumbá", "19°00'00.9\"S 57°38'16.1\"W", "P1"),
    ("Corumbá", "18°59'48.3\"S 57°39'23.3\"W", "Fundação de Turismo do Pantanal (CAT?)"),
    ("Corumbá", "19°01'41.9\"S 57°42'28.9\"W", "Aduana/Fronteira Guaicurus"),
    ("Corumbá", "18°59'48.7\"S 57°39'12.2\"W", "Anel Viário sul"),
    ("Corumbá", "19°00'32.0\"S 57°40'27.2\"W", "BR 262 acesso oeste"),
    ("Corumbá", "19°01'34.1\"S 57°37'07.2\"W", "Portal Corumbá BR-262"),
    # --- Ponta Pora ----------------------------------------------------------
    ("Ponta Porã", "22°31'32.2\"S 55°43'19.7\"W", "P3"),
    ("Ponta Porã", "22°33'07.8\"S 55°43'00.6\"W", "P2"),
    ("Ponta Porã", "22°31'48.5\"S 55°44'07.2\"W", "P1"),
    ("Ponta Porã", "22°30'56.5\"S 55°42'15.9\"W", "Contorno viário sul"),
    ("Ponta Porã", "22°33'37.2\"S 55°41'48.8\"W", "Rodoviária"),
    ("Ponta Porã", "22°33'06.7\"S 55°42'22.3\"W", "aeroporto"),
    ("Ponta Porã", "22°31'25.5\"S 55°44'01.3\"W", "Estação ferroviária"),
    ("Ponta Porã", "22°34'58.4\"S 55°41'07.5\"W", "BR-463 acesso sul"),
    ("Ponta Porã", "22°28'26.4\"S 55°45'00.7\"W", "MS-164 rota de acesso norte"),
    # --- Bonito --------------------------------------------------------------
    ("Bonito", "21°07'21.9\"S 56°24'27.7\"W", "P1: rodovia do turismo"),
    ("Bonito", "21°04'12.3\"S 56°34'27.7\"W", "P2: acesso a atrativos principais"),
    ("Bonito", "21°09'08.8\"S 56°30'16.8\"W", "P3"),
    ("Bonito", "21°14'38.8\"S 56°27'00.7\"W", "Aeroporto"),
    ("Bonito", "21°10'17.3\"S 56°27'11.0\"W", "MS-178 acesso monumento bem vindo a bonito"),
    ("Bonito", "21°06'07.5\"S 56°28'48.3\"W", "MS-345 acesso nordeste"),
    ("Bonito", "21°07'01.3\"S 56°30'23.0\"W", "MS-178 rotatoria acesso norte"),
    # --- Campo Grande --------------------------------------------------------
    ("Campo Grande", "20°28'03.4\"S 54°37'18.1\"W", "P3"),
    ("Campo Grande", "20°27'02.9\"S 54°37'10.8\"W", "P2"),
    ("Campo Grande", "20°27'27.2\"S 54°34'48.1\"W", "P1"),
    ("Campo Grande", "20°35'06.1\"S 54°34'59.4\"W", "BR-163 acesso ao sul do MS (Trevo Sul)"),
    ("Campo Grande", "20°27'52.0\"S 54°33'08.8\"W", "BR-262 acesso leste do MS (Jardim Noroeste)"),
    ("Campo Grande", "20°27'26.2\"S 54°40'07.4\"W", "aeroporto"),
    ("Campo Grande", "20°24'34.1\"S 54°43'52.4\"W", "BR-080 acesso ao norte do MS (Trevo da pedreira)"),
    ("Campo Grande", "20°33'08.5\"S 54°40'08.7\"W", "BR-060 acesso sudoeste do MS"),
    ("Campo Grande", "20°22'41.3\"S 54°32'15.8\"W", "(sem nota)"),
    ("Campo Grande", "20°28'39.9\"S 54°45'06.6\"W", "BR-262 acesso oeste MS"),
    # --- Guaira e Mundo Novo -------------------------------------------------
    ("Guaíra", "24°05'31.5\"S 54°11'40.8\"W", "PR-272 acesso Guaíra"),
    ("Guaíra", "24°05'19.4\"S 54°15'11.7\"W", "PA 3 Guaíra"),
    ("Guaíra", "24°05'16.6\"S 54°15'00.6\"W", "PA 2 Guaíra"),
    ("Guaíra", "24°04'29.0\"S 54°14'31.5\"W", "PA 1 Guaíra"),
    ("Guaíra", "24°04'47.4\"S 54°15'34.0\"W", "Av. Presidente Vargas 110"),
    ("Guaíra", "24°04'48.6\"S 54°11'15.0\"W", "aeroporto Guaíra"),
    ("Guaíra", "24°06'22.4\"S 54°14'20.7\"W", "BR-163 acesso Guaíra"),
    ("Mundo Novo", "24°01'40.1\"S 54°17'19.6\"W", "PA 3 Mundo Novo"),
    ("Mundo Novo", "23°56'08.4\"S 54°17'00.8\"W", "PA 2 Mundo Novo"),
    ("Mundo Novo", "24°00'11.5\"S 54°13'30.9\"W", "PA 1"),
    ("Mundo Novo", "23°56'13.2\"S 54°16'30.6\"W", "Avenida Campo Grande 200"),
    # --- Capanema ------------------------------------------------------------
    ("Capanema", "25°36'12.5\"S 53°45'05.1\"W", "acesso BR-163"),
    ("Capanema", "25°40'33.4\"S 53°47'46.6\"W", "CAT"),
    ("Capanema", "25°40'22.9\"S 53°48'25.9\"W", "rodoviária"),
    ("Capanema", "25°36'07.5\"S 53°58'12.3\"W", "Ponte fronteira BR-ARG"),
    ("Capanema", "25°37'05.1\"S 53°47'28.4\"W", "ponto 3"),
    ("Capanema", "25°40'12.3\"S 53°48'30.4\"W", "Ponto 2"),
    ("Capanema", "25°35'57.9\"S 53°54'38.2\"W", "Ponto 1"),
    # --- Barracao e Dionisio Cerqueira ---------------------------------------
    ("Barracão", "26°14'58.0\"S 53°38'11.0\"W", "Rua Minas Gerais 443"),
    ("Barracão", "26°14'50.7\"S 53°38'21.5\"W", "Barracão ponto 3"),
    ("Barracão", "26°14'28.0\"S 53°27'21.8\"W", "Barracão ponto 2"),
    ("Barracão", "26°14'04.3\"S 53°34'59.4\"W", "Barracão ponto 1"),
    ("Dionísio Cerqueira", "26°42'54.0\"S 53°31'02.2\"W", "DC BR-163 acesso"),
    ("Dionísio Cerqueira", "26°17'58.0\"S 53°36'56.6\"W", "DC ponto 3"),
    ("Dionísio Cerqueira", "26°15'19.1\"S 53°38'10.2\"W", "DC ponto 2"),
    ("Dionísio Cerqueira", "26°17'14.4\"S 53°33'19.7\"W", "DC ponto 1"),
    # --- Medianeira (informado diretamente) ----------------------------------
    ("Medianeira", "-25.301259|-54.081708", "Rotatória = Ponto 1"),
]

# Pino que a propria equipe marcou como invalido - preservado como registro.
DESCARTADOS = [
    ("Dionísio Cerqueira", "25°15'07.5\"S 52°01'17.6\"W",
     "DC rodoviária [errado]",
     "A equipe anotou o pino como errado na própria lista. Resolve para "
     "Goioxim (PR), a 173 km. Confirma o diagnóstico de troca de UF no endereço."),
]


def para_decimal(txt: str) -> tuple[float, float]:
    if "|" in txt:
        a, b = txt.split("|")
        return float(a), float(b)
    partes = txt.split()
    lat, _ = parse_coordenadas(partes[0])
    lon, _ = parse_coordenadas(partes[1])
    return lat, lon


# ==============================================================================
# CRUZAMENTO POR PROXIMIDADE
# ==============================================================================
cons = gpd.read_file(CONSOLIDADO)
cons_m = cons.to_crs("EPSG:5880")

# Corte acima do qual nao se declara correspondencia. Um pino distante de tudo
# no municipio e quase sempre um ponto planejado que NAO chegou a ser levantado
# (marcado "NAO HOUVE COLETA" no catalogo) - e nao um ponto mal pareado.
CORTE_M = 1500.0

linhas = []
for cidade, grupo in pd.DataFrame(
        PINOS, columns=["cidade", "coord", "rotulo"]).groupby("cidade", sort=False):

    alvos = cons_m[cons_m.cidade == cidade]
    pinos_xy = []
    for _, g in grupo.iterrows():
        lat, lon = para_decimal(g["coord"])
        pinos_xy.append((g["rotulo"], lat, lon,
                         gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326")
                         .to_crs("EPSG:5880").iloc[0]))

    if alvos.empty:
        for rot, lat, lon, _ in pinos_xy:
            linhas.append({"cidade_lista": cidade, "rotulo_campo": rot,
                           "lat": round(lat, 6), "lon": round(lon, 6),
                           "ponto_consolidado": "", "ordem": "",
                           "cidade_consolidado": "", "categoria": "",
                           "formulario": "", "distancia_m": None})
        continue

    # Matriz de custo pino x ponto, com atribuicao otima um-para-um.
    # Sem isso, dois pinos disputam o mesmo ponto e ambos ficam errados.
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    idx_alvos = list(alvos.index)
    custo = np.full((len(pinos_xy), len(idx_alvos)), 1e9)
    for i, (_, _, _, geom) in enumerate(pinos_xy):
        for j, k in enumerate(idx_alvos):
            custo[i, j] = geom.distance(cons_m.geometry.loc[k])

    # Penaliza pares acima do corte para que a otimizacao prefira deixar o
    # pino sem par a arrastar um ponto distante.
    custo_ajustado = np.where(custo > CORTE_M, 1e9, custo)
    li, lj = linear_sum_assignment(custo_ajustado)
    pares = {int(a): int(b) for a, b in zip(li, lj)
             if custo_ajustado[a, b] < 1e9}

    for i, (rot, lat, lon, _) in enumerate(pinos_xy):
        base = {"cidade_lista": cidade, "rotulo_campo": rot,
                "lat": round(lat, 6), "lon": round(lon, 6)}
        if i in pares:
            k = idx_alvos[pares[i]]
            base.update({
                "ponto_consolidado": cons.loc[k, "nome_ponto"],
                "ordem": cons.loc[k, "ordem"],
                "cidade_consolidado": cons.loc[k, "cidade"],
                "categoria": cons.loc[k, "categoria"],
                "formulario": cons.loc[k, "formulario"],
                "distancia_m": round(float(custo[i, pares[i]]), 1),
            })
        else:
            mais_perto = float(custo[i].min())
            base.update({
                "ponto_consolidado": "", "ordem": "", "cidade_consolidado": "",
                "categoria": "", "formulario": "", "distancia_m": None,
                "ponto_mais_proximo": cons.loc[idx_alvos[int(custo[i].argmin())],
                                               "nome_ponto"],
                "dist_mais_proximo_m": round(mais_perto, 1),
            })
        linhas.append(base)

r = pd.DataFrame(linhas)


def confianca(m) -> str:
    if m is None or pd.isna(m):
        return "SEM CORRESPONDÊNCIA"
    if m <= 150:
        return "alta"
    if m <= 600:
        return "média"
    return "baixa — conferir"


r["confiança"] = r.distancia_m.map(confianca)

print("=" * 96)
print("PINOS DE CAMPO -> PONTOS DE AFERIÇÃO (por proximidade)")
print("=" * 96)
for cidade, sub in r.groupby("cidade_lista", sort=False):
    print(f"\n--- {cidade} ---")
    for _, x in sub.sort_values("distancia_m", na_position="last").iterrows():
        alerta = "" if x["cidade_lista"] == x["cidade_consolidado"] else \
            f"  [!! consolidado diz {x['cidade_consolidado']}]"
        print(f"  {x['rotulo_campo'][:42]:<42} -> {x['ordem']:<10} "
              f"{str(x['ponto_consolidado'])[:40]:<40} {x['distancia_m']:>8.0f} m  "
              f"{x['confiança']}{alerta}")

# --- pontos consolidados que nenhum pino alcancou ----------------------------
usados = set(zip(r.cidade_consolidado, r.ordem))
faltam = [(c, o, n) for c, o, n in
          zip(cons.cidade, cons.ordem, cons.nome_ponto)
          if (c, o) not in usados]
print("\n" + "-" * 96)
print(f"PONTOS CONSOLIDADOS SEM PINO CORRESPONDENTE — {len(faltam)}")
print("-" * 96)
for c, o, n in faltam:
    print(f"  {c:<22} {o:<10} {n}")

xlsx = DIR_DADOS / "pinos_campo_para_pontos.xlsx"
with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
    r.to_excel(w, sheet_name="Pinos x pontos", index=False)
    pd.DataFrame(DESCARTADOS, columns=["cidade", "coordenada", "rótulo", "motivo"]
                 ).to_excel(w, sheet_name="Pinos descartados", index=False)
    pd.DataFrame(faltam, columns=["cidade", "ordem", "nome_ponto"]
                 ).to_excel(w, sheet_name="Sem pino", index=False)
print(f"\nPlanilha: {xlsx}")
