"""
Pontos que estavam no plano de campo e nao foram aferidos.

A planilha de planejamento (`georreferenciamento.xlsx`) registra, nas abas
"Pontos de coleta PR + Mundo Nov" e "Pontos de coleta MS", linhas marcadas
como "nao houve coleta" / "nao coletado". Sao pontos previstos cuja ficha
nao existe: nao entram na analise, mas delimitam o seu alcance.

Este script fixa esse levantamento no acervo, para que a analise nao dependa
de um arquivo fora do projeto. Saida:

    <CAMPO>/03_Pontos_Afericao/pontos_planejados_sem_coleta.json

Uso:
    python 32_pontos_planejados_sem_coleta.py [caminho/para/georreferenciamento.xlsx]
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from comum import CAMPO, JOTFORM, MUNICIPIOS                     # noqa: E402

PADRAO = JOTFORM / "georreferenciamento.xlsx"
SAIDA = CAMPO / "03_Pontos_Afericao" / "pontos_planejados_sem_coleta.json"

# a terceira coluna nao quer dizer a mesma coisa nas duas abas: no PR e a
# razao de escolha do ponto; no MS e o endereco, quase sempre mais preciso
# que o proprio nome
ABAS = {
    "Pontos de coleta PR + Mundo Nov": ("Município", "Ponto de Coleta",
                                        "Motivação/escolha", "motivo"),
    "Pontos de coleta MS": ("municipio", "nome_ponto_afericao",
                            "Endereço", "local"),
}


def arrumar(s: str) -> str:
    """Espacamento das siglas de rodovia: 'BR - 163' e 'MS - 080'."""
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return re.sub(r"\b(BR|PR|MS|SC)\s*-\s*(\d)", r"\1-\2", s, flags=re.I)


def _chave(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())


# "MS - Ponta Porã", "Campo grande", "Foz do Iguaçu" -> o municipio do caderno
POR_CHAVE = {_chave(m.nome): m for m in MUNICIPIOS}


def municipio(bruto: str):
    c = _chave(re.sub(r"^\s*[A-Z]{2}\s*-\s*", "", str(bruto)))
    return POR_CHAVE.get(c)


def sem_coleta(linha) -> bool:
    texto = " ".join(str(v) for v in linha.values)
    return bool(re.search(r"n[aã]o\s+(houve\s+coleta|coletado)", texto,
                          flags=re.I))


def main(caminho: Path) -> None:
    livro = pd.ExcelFile(caminho)
    fora, achados = [], {}
    for aba, (c_mun, c_ponto, c_obs, papel) in ABAS.items():
        d = livro.parse(aba, dtype=str)
        for _, r in d[d.apply(sem_coleta, axis=1)].iterrows():
            m = municipio(r.get(c_mun, ""))
            if m is None:
                fora.append(f"{aba}: {r.get(c_mun)}")
                continue
            nome = arrumar(r.get(c_ponto, ""))
            obs = arrumar(r.get(c_obs, ""))
            obs = "" if obs.lower() in ("", "nan") else obs
            item = {"nome": nome}
            if papel == "local" and obs:
                # o endereco costuma repetir o nome e acrescentar o trecho:
                # quando repete, ele proprio ja e o nome melhor
                item["nome"] = obs if _chave(nome) in _chave(obs) else nome
                if item["nome"] != obs:
                    item["local"] = obs
            elif obs:
                item["motivo"] = obs[0].lower() + obs[1:]
            achados.setdefault(m.slug, {"municipio": m.nome_uf,
                                        "pontos": []})["pontos"].append(item)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(
        {"fonte": ("Planejamento de campo (georreferenciamento.xlsx), "
                   "linhas marcadas como sem coleta"),
         "por_municipio": dict(sorted(achados.items()))},
        ensure_ascii=False, indent=1), encoding="utf-8")

    for slug, bloco in sorted(achados.items()):
        print(f"{bloco['municipio']}: {len(bloco['pontos'])} ponto(s)")
        for p in bloco["pontos"]:
            extra = p.get("local") or p.get("motivo") or ""
            print(f"   {p['nome']}" + (f"  — {extra}" if extra else ""))
    if fora:
        print("\nsem municipio correspondente:", *fora, sep="\n   ")
    print(f"\n{SAIDA}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else PADRAO)
