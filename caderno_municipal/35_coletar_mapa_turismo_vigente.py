# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
CATEGORIA E REGIAO TURISTICA NO MAPA DO TURISMO VIGENTE
================================================================================
O 10_coletar_mtur.py pega a categorizacao no portal de dados abertos, cujo
recurso mais recente e o de 2019 (letras A a E). O Mapa do Turismo em vigor,
publicado em https://www.mapa.turismo.gov.br, usa outras tres categorias
(municipio turistico, com oferta turistica complementar, de apoio ao
turismo), e a passagem de uma para a outra nao e automatica: municipios com
letra em 2019 podem ter outra categoria, ou nao constar, no Mapa vigente.

Este script consulta a mesma API que o site usa e guarda:

    09_Base_Socioeconomica_Municipal/08_MTur_Dados_Abertos/
        nacional/mapa_turismo_vigente_<ano>.csv   todos os municipios do Mapa
        recorte_12/mapa_turismo_vigente.json      os 12 do estudo, com os que
                                                  nao constam marcados

A busca e pelo codigo IBGE e pela UF, porque ha homonimos em outros estados
(Barracao/RS, Bonito/BA, Mundo Novo/GO, Guaira/SP etc.).
================================================================================
"""
from __future__ import annotations

import csv
import io
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import ACERVO, MUNICIPIOS  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = ACERVO / "09_Base_Socioeconomica_Municipal" / "08_MTur_Dados_Abertos"
NACIONAL = BASE / "nacional"
RECORTE = BASE / "recorte_12"

SITE = "https://www.mapa.turismo.gov.br/mapa/init.html#/home"
API = "https://www.mapa.turismo.gov.br/mapa/rest/publico/regionalizacao"

# Rotulos do filtro "Municipios Categorizados" do proprio site
CATEGORIAS = {
    "1": "Município turístico",
    "2": "Município com oferta turística complementar",
    "3": "Município de apoio ao turismo",
}


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def _post(url: str, corpo: dict):
    req = urllib.request.Request(
        url, data=json.dumps(corpo).encode("utf-8"),
        headers={"User-Agent": "Mozilla/5.0",
                 "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def main() -> None:
    resumo = _get(f"{API}/resumo")
    ano = str(resumo["ano"])
    todos = _post(f"{API}/pesquisar", {
        "nuRegiao": None, "nuUf": None, "nuLocalidade": None,
        "noRegiaoTuristica": None, "colCluster": []})
    if len(todos) != resumo["totalMunicipios"]:
        raise SystemExit(f"a API devolveu {len(todos)} municípios, o resumo "
                         f"diz {resumo['totalMunicipios']}")

    NACIONAL.mkdir(parents=True, exist_ok=True)
    RECORTE.mkdir(parents=True, exist_ok=True)
    campos = ["nuMunicipioIbge", "noMunicipio", "sgUf", "noRegiaoTuristica",
              "coCluster", "noInstancia", "flSituacaoConselho", "ano"]
    saida_nac = NACIONAL / f"mapa_turismo_vigente_{ano}.csv"
    with open(saida_nac, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(campos + ["categoria"])
        for r in sorted(todos, key=lambda r: (r["sgUf"], r["noMunicipio"])):
            w.writerow([r.get(c) for c in campos]
                       + [CATEGORIAS.get(str(r.get("coCluster")), "")])

    por_ibge = {str(r["nuMunicipioIbge"]): r for r in todos}
    municipios = {}
    for m in MUNICIPIOS:
        r = por_ibge.get(str(m.codigo_ibge))
        if r is not None and r["sgUf"] != m.uf:
            raise SystemExit(f"{m.nome}: código IBGE em outra UF ({r['sgUf']})")
        municipios[m.nome] = {
            "codigo_ibge": m.codigo_ibge,
            "uf": m.uf,
            "consta": r is not None,
            "categoria": CATEGORIAS.get(str(r["coCluster"])) if r else None,
            "co_cluster": str(r["coCluster"]) if r else None,
            "regiao_turistica": r["noRegiaoTuristica"] if r else None,
        }
    registro = {
        "fonte": "Ministério do Turismo, Mapa do Turismo Brasileiro",
        "edicao": ano,
        "site": SITE,
        "api": f"{API}/pesquisar",
        "acesso": date.today().isoformat(),
        "total_municipios_no_mapa": resumo["totalMunicipios"],
        "total_regioes": resumo["totalRegioes"],
        "categorias": CATEGORIAS,
        "municipios": municipios,
    }
    saida = RECORTE / "mapa_turismo_vigente.json"
    saida.write_text(json.dumps(registro, ensure_ascii=False, indent=2),
                     encoding="utf-8")

    print(f"Mapa do Turismo {ano}: {len(todos)} municípios -> {saida_nac.name}")
    for nome, v in municipios.items():
        print(f"  {nome:20s} {v['categoria'] or 'NÃO CONSTA':45s} "
              f"{v['regiao_turistica'] or ''}")


if __name__ == "__main__":
    main()
