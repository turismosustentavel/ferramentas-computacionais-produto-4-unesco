# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
HIERARQUIA DOS ATRATIVOS - A TABELA DE RELEVANCIA
================================================================================
A hierarquizacao oficial dos atrativos e a do relatorio
`Atrativos_Relevantes_Por_Cidade.md` (Selecao dos pontos para afericao): cinco
atrativos por municipio, ordenados por pesquisa qualitativa e netnografica -
blogs de viagem, portais especializados, vlogs do YouTube e TripAdvisor -,
combinando recorrencia digital, volume e nota de avaliacoes e escopo
geografico de atratividade.

Este modulo le essa tabela e a casa com a camada georreferenciada de
atrativos, para que todas as etapas usem a mesma hierarquia.
Onde o relatorio nao cobre o municipio, vale o RANK_PROD4 da camada.
================================================================================
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from comum import PRODUCAO

RELATORIO = (PRODUCAO / "Seleção dos pontos para aferição" /
             "Atrativos_Relevantes_Por_Cidade.md")


def _chave(s: str) -> str:
    t = unicodedata.normalize("NFKD", str(s or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"\*+|\(.*?\)", " ", t)
    t = re.sub(r"[^a-zA-Z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def _limpar(md: str) -> str:
    """Tira o negrito do Markdown; o separador escapado '\\|' vira ' | '."""
    return re.sub(r"\*\*", "", md.replace("\\|", " | ")).strip()


def tabela(nome_municipio: str) -> list[dict]:
    """As cinco linhas da tabela de relevância do município, ou []."""
    if not RELATORIO.exists():
        return []
    texto = RELATORIO.read_text("utf-8")
    alvo = _chave(nome_municipio)
    secoes = re.findall(r"^### \d+\.\d+\. (.+?)\n(.*?)(?=^### |^## )", texto,
                        re.S | re.M)
    for titulo, corpo in secoes:
        if _chave(titulo).startswith(alvo):
            break
    else:
        return []
    linhas = []
    for l in corpo.splitlines():
        if not l.startswith("| **") or "º" not in l:
            continue
        # divide nas barras que NAO estao escapadas ("\|" e texto da celula)
        cels = [_limpar(c) for c in
                re.split(r"(?<!\\)\|", l.strip().strip("|"))]
        if len(cels) < 6:
            continue
        rank = int(re.sub(r"\D", "", cels[0]))
        linhas.append({"rank": rank, "atrativo": cels[1], "categoria": cels[2],
                       "dimensao": cels[3], "recorrencia": cels[4],
                       "tripadvisor": cels[5]})
    # padroes de visitacao (permanencia, horario, perfil)
    for l in corpo.splitlines():
        mm = re.match(r"^\d+\. \*\*(.+?)\*\*: (.+)$", l.strip())
        if mm:
            nome = set(_chave(mm.group(1)).split()) - {"de", "do", "da", "das", "dos"}
            for r in linhas:
                alvo = set(_chave(r["atrativo"]).split()) - {"de", "do", "da",
                                                            "das", "dos"}
                # 'Usina de Itaipu' na lista x 'Usina Hidreletrica de Itaipu'
                if nome and nome <= alvo:
                    r["visitacao"] = mm.group(2).strip()
    return sorted(linhas, key=lambda r: r["rank"])


def _semelhanca(tabela_nome: str, camada_nome: str) -> float:
    """Parecença entre o nome da tabela e um nome da camada.

    A contenção de tokens só vale no sentido tabela ⊂ camada e é penalizada
    por cada token excedente: 'Cataratas do Iguaçu' está contido em
    'Aeroporto Internacional de Foz do Iguaçu/Cataratas', mas com cinco
    tokens a mais — não é o mesmo lugar.
    """
    a, b = _chave(tabela_nome), _chave(camada_nome)
    if not a or not b:
        return 0.0
    ta, tb = set(a.split()) - {"de", "do", "da", "dos", "das"}, set(b.split())
    contido = (1.0 - 0.15 * len(tb - ta - {"de", "do", "da", "dos", "das"})
               if ta and ta <= tb else 0.0)
    return max(SequenceMatcher(None, a, b).ratio(), contido)


# nome da tabela -> como o MESMO atrativo esta grafado na camada. Sem isto,
# "Cataratas do Iguacu" cai por parecenca em "Cataratas del Iguazu - Arg.".
PREFERIDOS = {
    "cataratas do iguacu": "cataratas do iguacu brasil",
    "usina hidreletrica de itaipu": "turismo itaipu",
}
# outros registros da camada que pertencem ao mesmo complexo e recebem o
# mesmo posto, sem rotulo proprio
SINONIMOS = {
    "usina hidreletrica de itaipu": ["itaipu panoramica", "itaipu iluminada",
                                      "itaipu refugio biologico"],
}


def ranquear(gdf, nome_municipio: str, coluna_nome: str = "NOME"):
    """Devolve o gdf com a coluna 'ord' (1–5 pela tabela; 99 os demais).

    Cada linha da tabela é atribuída ao registro mais parecido da camada; as
    entradas listadas em SINONIMOS recebem o mesmo posto (a Usina de Itaipu é
    um complexo com vários produtos no mesmo endereço).
    """
    g = gdf.copy()
    g["ord"] = 99
    g["rotulo"] = g[coluna_nome].astype(str)
    g["principal"] = False          # registro que carrega o nome da tabela
    linhas = tabela(nome_municipio)
    if not linhas:
        def _r(v):
            t = str(v or "").rstrip("º")
            return int(t) if t.isdigit() else 99
        if "RANK_PROD4" in g.columns:
            g["ord"] = g.RANK_PROD4.map(_r)
        return g, []
    nomes = g[coluna_nome].astype(str).tolist()
    usados = set()
    for r in linhas:
        alvo = _chave(r["atrativo"])
        # o melhor registro para o nome da tabela recebe o rotulo da tabela;
        # os sinonimos (produtos do mesmo complexo) recebem so o posto
        principal = PREFERIDOS.get(alvo, alvo)
        for cand in [principal] + SINONIMOS.get(alvo, []):
            scores = [(_semelhanca(cand, n), i) for i, n in enumerate(nomes)
                      if i not in usados]
            if not scores:
                continue
            s, i = max(scores)
            if s >= 0.6:
                g.iloc[i, g.columns.get_loc("ord")] = r["rank"]
                usados.add(i)
                if cand == principal:
                    g.iloc[i, g.columns.get_loc("rotulo")] = r["atrativo"]
                    g.iloc[i, g.columns.get_loc("principal")] = True
    # Posto da tabela sem registro parecido: vale o posto que a própria
    # camada traz (RANK_PROD4). Em Guaíra, "Rio Paraná e Passeios de Barco"
    # não se parecia com nenhum nome, e a hierarquia pulava do 1º para o 3º;
    # na camada, o 2º é o registro "Rio Paraná".
    if "RANK_PROD4" in g.columns:
        for r in linhas:
            if (g.principal & (g.ord == r["rank"])).any():
                continue
            cands = [i for i in range(len(g)) if i not in usados and
                     str(g.iloc[i].RANK_PROD4).strip() == f"{r['rank']}º"]
            if not cands:
                continue
            i = max(cands, key=lambda k: _semelhanca(r["atrativo"],
                                                       nomes[k]))
            g.iloc[i, g.columns.get_loc("ord")] = r["rank"]
            g.iloc[i, g.columns.get_loc("rotulo")] = r["atrativo"]
            g.iloc[i, g.columns.get_loc("principal")] = True
            usados.add(i)
    return g, linhas
