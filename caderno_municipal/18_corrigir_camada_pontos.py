# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
CORRECOES NA CAMADA CONSOLIDADA DE PONTOS DE AFERICAO
================================================================================
A camada `pontos_afericao_consolidados.geojson` veio do planejamento. O campo
mostrou que alguns registros nao correspondem ao que foi levantado. Este script
aplica as correcoes confirmadas pela coordenacao, guarda copia da camada
original e registra cada alteracao.

Idempotente: pode ser executado quantas vezes for preciso.

Os NOMES nao se corrigem aqui: eles vem da sintese de campo, por
`31_nomes_oficiais_pontos.py`, que e a autoridade. Este script trata do que a
sintese nao traz — coordenada e categoria.

CORRECOES
    Foz do Iguacu, Ponto #4
        A coordenada estava 9,7 km ao norte, a 1 km do Ponto #3, e os dois
        pareciam duplicados. A area de analise da sintese mostra que sao
        pontos distintos; a coordenada correta veio da coordenacao.

    Foz do Iguacu, Ponto #6
        A camada trazia uma "aduana" no centro urbano, a 300 m do Ponto #2
        (BR-277 x Av. Costa e Silva). Nao existe aduana ali: era o proprio
        ponto de acesso, duplicado com outra categoria. As aduanas de Foz sao
        as duas pontes (#9 e #10). O registro passa a ser o ponto que foi
        levantado em campo e nao constava da camada: o Mercado Publico
        Barrageiro, na Vila A (Av. Araucaria, 140), ficha Geral "P3".
        Coordenada: Google Maps, place "Mercado Publico Barrageiro".
================================================================================
"""
from __future__ import annotations

import io
import shutil
import sys
from datetime import date
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).parent))
from comum import CAMPO                                          # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CONSOLIDADO = (CAMPO / "03_Pontos_Afericao" / "vetores_gis" /
               "pontos_afericao_consolidados.geojson")
BACKUP = CONSOLIDADO.with_name("pontos_afericao_consolidados_ORIGINAL.geojson")

# (cidade, ordem) -> novos atributos
CORRECOES = {
    # Os pontos #3 e #4 pareciam duplicados: dois registros a 994 m um do
    # outro, ambos chamados "Avenida das Cataratas", descrevendo mobiliário
    # incompatível. O plano de coleta (georreferenciamento.xlsx, aba "Pontos
    # de coleta PR + Mundo Nov") mostra que são dois pontos distintos e
    # previstos — a rotatória do Catuaí, na rota de acesso sul, e o acesso
    # aos atrativos. A camada deu aos dois o nome da avenida; os nomes vêm
    # depois da síntese de campo (31). Aqui se corrige a coordenada do #4.
    ("Foz do Iguaçu", "Ponto #4"): {
        "latitude": -25.614091,
        "longitude": -54.480673,
        "_motivo": "A coordenada estava 9,7 km ao norte, a 1 km do Ponto #3, "
                   "e os dois pareciam duplicados. A área de análise da "
                   "síntese de campo é 'via interna de acesso aos atrativos "
                   "turísticos principais': o ponto está na Av. das Cataratas "
                   "entre o aeroporto e a entrada do Parque Nacional. "
                   "Coordenada confirmada pela coordenação.",
    },
    ("Foz do Iguaçu", "Ponto #6"): {
        "categoria": "Via Urbana / Atrativo Central",
        "tipo_via": "Via urbana",
        "formulario": "Formulário Geral",
        "latitude": -25.5044155,
        "longitude": -54.5825597,
        "_motivo": "Aduana inexistente, duplicada com o Ponto #2; a "
                   "coordenada passa a ser a do ponto levantado em campo "
                   "(ficha Geral 'P3', Mercado Público Barrageiro, Vila A).",
    },
}

if not BACKUP.exists():
    shutil.copy2(CONSOLIDADO, BACKUP)
    print(f"cópia da camada original: {BACKUP.name}")

g = gpd.read_file(CONSOLIDADO)
if "correcao" not in g.columns:
    g["correcao"] = None

aplicadas = 0
for (cidade, ordem), novo in CORRECOES.items():
    sel = (g.cidade == cidade) & (g.ordem == ordem)
    if sel.sum() != 1:
        print(f"! {cidade} {ordem}: {sel.sum()} registros — ignorado")
        continue
    i = g.index[sel][0]
    # idempotencia: so pula quando TODOS os campos ja estao como devem —
    # olhar so o nome deixava passar uma correcao de coordenada
    def _igual(k, v):
        atual = g.at[i, k]
        if isinstance(v, float):
            return atual is not None and abs(float(atual) - v) < 1e-6
        return str(atual) == str(v)

    if all(_igual(k, v) for k, v in novo.items() if not k.startswith("_")):
        continue
    antes = g.at[i, "nome_ponto"]        # só para o registro da alteração
    for k, v in novo.items():
        if not k.startswith("_"):
            g.at[i, k] = v
    if "latitude" in novo:                       # correção de posição
        g.at[i, "geometry"] = Point(novo["longitude"], novo["latitude"])
    g.at[i, "correcao"] = (f"{date.today():%Y-%m-%d}: era '{antes}'. "
                           + novo["_motivo"])
    aplicadas += 1
    print(f"{cidade} {ordem} ({antes}): "
          + ", ".join(k for k in novo if not k.startswith("_")))

if aplicadas:
    g.to_file(CONSOLIDADO, driver="GeoJSON")
    gpkg = CONSOLIDADO.with_suffix(".gpkg")
    if gpkg.exists():
        g.to_file(gpkg, driver="GPKG")
print(f"{aplicadas} correção(ões) aplicada(s) · {len(g)} pontos na camada")
