# -*- coding: utf-8 -*-
"""
================================================================================
CADERNO DE INFORMACOES POR MUNICIPIO | PRODUTO 4
COLETA DOS DADOS ABERTOS DO MINISTERIO DO TURISMO
================================================================================
Fecha as duas lacunas que as bases estaduais nao cobrem de forma uniforme:

  IGR e regiao turistica   -> Mapa do Turismo Brasileiro
  Cadastur                 -> os prestadores publicados por categoria

Vantagem sobre as fontes estaduais: sao nacionais, entao cobrem PR, MS e SC no
mesmo metodo e no mesmo ano - inclusive Dionisio Cerqueira, que nem o IPARDES
nem a SEMADESC atendem.

O portal e um CKAN (dados.turismo.gov.br) e cada conjunto publica um recurso por
ano. Este script toma o ano mais recente de cada conjunto, baixa, e guarda duas
versoes: o arquivo nacional como veio e o recorte dos 12 municipios do estudo.

SAIDA
    09_Base_Socioeconomica_Municipal/08_MTur_Dados_Abertos/
        nacional/    arquivos como publicados
        recorte_12/  linhas dos municipios do estudo
================================================================================
"""
from __future__ import annotations

import gzip
import io
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from comum import ACERVO, MUNICIPIOS, normalizar_municipio  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = ACERVO / "09_Base_Socioeconomica_Municipal" / "08_MTur_Dados_Abertos"
NACIONAL = BASE / "nacional"
RECORTE = BASE / "recorte_12"
for d in (NACIONAL, RECORTE):
    d.mkdir(parents=True, exist_ok=True)

API = "https://dados.turismo.gov.br/api/3/action"

CONJUNTOS = [
    # (id no portal, rotulo curto)
    ("mapa-do-turismo-brasileiro", "mapa_do_turismo"),
    ("categorizacao", "categorizacao_municipios"),
    ("indice-de-competitividade", "indice_competitividade"),
    ("empregos-formais-no-turismo", "empregos_formais_turismo"),
    ("meios-de-hospedagem", "cadastur_meios_de_hospedagem"),
    ("agencia-de-turismo", "cadastur_agencias"),
    ("restaurantes-cafeterias-e-bares", "cadastur_alimentacao"),
    ("transportadora-turistica", "cadastur_transportadoras"),
    ("empreendimento-de-apoio-ao-turismo-nautico-ou-a-pesca-desportiva",
     "cadastur_nautico_e_pesca"),
    ("acampamento-turistico", "cadastur_acampamentos"),
    ("parque-tematico", "cadastur_parques_tematicos"),
    ("organizador-de-eventos", "cadastur_organizadores_eventos"),
    ("locadora-de-veiculos", "cadastur_locadoras"),
    ("centro-de-convencoes", "cadastur_centros_convencoes"),
    ("empreendimento-de-entretenimento-e-lazer-e-parques-aquaticos",
     "cadastur_entretenimento_lazer"),
    ("prestador-especializado-em-segmentos-turisticos",
     "cadastur_prestadores_especializados"),
    ("prestadores-de-servicos-turisticos-guia-turismo_2", "cadastur_guias"),
    ("casas-de-espetaculos-e-equipamentos-de-animacao-turistica",
     "cadastur_casas_espetaculo"),
]


def buscar_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Accept-Encoding": "gzip"})
    resp = urllib.request.urlopen(req, timeout=120)
    raw = resp.read()
    if resp.headers.get("Content-Encoding") == "gzip":
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def baixar(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=300).read()


def ano_do_recurso(nome: str) -> int:
    """O nome do recurso costuma ser o ano, as vezes um intervalo (2017/2018)."""
    anos = re.findall(r"(20\d{2})", str(nome))
    return max(int(a) for a in anos) if anos else -1


def ler_tabela(bruto: bytes) -> pd.DataFrame | None:
    """Le o CSV escolhendo o encoding que de fato decodifica o arquivo.

    Tentar utf-8 de forma tolerante antes do latin-1 produz texto corrompido
    que passa despercebido: "Municipio" vira mojibake, a normalizacao nao
    reconhece nenhum nome e o recorte sai vazio sem erro aparente. Por isso o
    utf-8 e testado em modo estrito primeiro; se nao decodificar, usa latin-1.
    """
    # Alguns conjuntos do portal estao rotulados como CSV mas sao planilhas
    # binarias: o Mapa do Turismo e a Categorizacao vem como .xls (assinatura
    # OLE2) e o leitor de CSV devolveria lixo silenciosamente.
    if bruto[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        try:
            return pd.read_excel(io.BytesIO(bruto), dtype=str)
        except Exception:
            return None
    if bruto[:4] == b"PK\x03\x04":
        # Pode ser .xlsx (que tambem e um zip) ou um zip contendo o CSV - o
        # conjunto de empregos formais no turismo publica a RAIS assim, num
        # arquivo de 57 MB rotulado como CSV no portal.
        import zipfile
        try:
            z = zipfile.ZipFile(io.BytesIO(bruto))
            nomes = z.namelist()
        except Exception:
            return None
        if any(n == "[Content_Types].xml" for n in nomes):
            try:
                return pd.read_excel(io.BytesIO(bruto), dtype=str)
            except Exception:
                return None
        internos = [n for n in nomes
                    if n.lower().endswith((".csv", ".txt", ".xls", ".xlsx"))]
        if not internos:
            return None
        maior = max(internos, key=lambda n: z.getinfo(n).file_size)
        return ler_tabela(z.read(maior))

    encs = []
    for e in ("utf-8-sig", "utf-8"):
        try:
            bruto.decode(e)
            encs.append(e)
            break
        except UnicodeDecodeError:
            pass
    encs.append("latin-1")

    melhor = None
    for enc in encs:
        for sep in (";", ",", "\t"):
            try:
                d = pd.read_csv(io.BytesIO(bruto), encoding=enc, sep=sep,
                                dtype=str, low_memory=False,
                                on_bad_lines="skip")
            except Exception:
                continue
            if d.shape[1] > 1 and (melhor is None or
                                   d.shape[1] > melhor.shape[1]):
                melhor = d
        if melhor is not None:
            return melhor
    return melhor


def coluna_municipio(d: pd.DataFrame) -> str | None:
    for c in d.columns:
        k = str(c).strip().lower()
        if k in ("municipio", "município", "nome_municipio", "nm_municipio",
                 "cidade", "municipio_nome", "destino", "nome do municipio",
                 "nome do município"):
            return c
    for c in d.columns:
        if "munic" in str(c).lower():
            return c
    return None


CODIGOS = {m.codigo_ibge for m in MUNICIPIOS}
resumo = []

for ident, rotulo in CONJUNTOS:
    try:
        pacote = buscar_json(f"{API}/package_show?id={ident}")["result"]
    except Exception as e:
        print(f"  ERRO  {rotulo:<38} {str(e)[:50]}")
        continue

    csvs = [r for r in pacote.get("resources", [])
            if str(r.get("format", "")).upper() == "CSV"]
    if not csvs:
        print(f"  --    {rotulo:<38} sem recurso CSV")
        continue

    rec = max(csvs, key=lambda r: ano_do_recurso(r.get("name", "")))
    ano = rec.get("name", "?")
    try:
        bruto = baixar(rec["url"])
        d = ler_tabela(bruto)
    except Exception as e:
        print(f"  ERRO  {rotulo:<38} download: {str(e)[:44]}")
        continue
    if d is None or d.empty:
        print(f"  --    {rotulo:<38} não foi possível ler o CSV")
        continue

    (NACIONAL / f"{rotulo}_{ano}.csv".replace("/", "-")).write_bytes(bruto)

    # --- recorte dos 12 municipios -----------------------------------------
    cm = coluna_municipio(d)
    n_rec = 0
    if cm:
        marca = d[cm].map(lambda v: normalizar_municipio(v))
        # so aceita quando a UF tambem confere, para nao capturar homonimos
        cuf = next((c for c in d.columns
                    if str(c).strip().lower() in ("uf", "sigla_uf", "estado",
                                                  "uf_sigla")), None)
        ok = marca.notna()
        if cuf is not None:
            confere_uf = pd.Series(
                [(m is not None and str(u).strip().upper()[:2] == m.uf)
                 for m, u in zip(marca, d[cuf])], index=d.index)
            ok = ok & confere_uf
        sub = d[ok].copy()
        if not sub.empty:
            sub.insert(0, "codigo_ibge",
                       [m.codigo_ibge for m in marca[ok]])
            sub.insert(1, "municipio_canonico", [m.nome for m in marca[ok]])
            sub.to_csv(RECORTE / f"{rotulo}.csv", index=False,
                       encoding="utf-8-sig")
            n_rec = len(sub)

    resumo.append({"conjunto": rotulo, "recurso": ano,
                   "linhas_nacional": len(d), "linhas_12_municipios": n_rec,
                   "coluna_municipio": cm or "(não encontrada)"})
    print(f"  ok    {rotulo:<38} {ano:<12} nacional {len(d):>7,} · "
          f"recorte {n_rec:>5,}")
    time.sleep(0.5)

R = pd.DataFrame(resumo)
R.to_csv(BASE / "resumo_da_coleta.csv", index=False, encoding="utf-8-sig")
(BASE / "procedencia.json").write_text(json.dumps({
    "coletado_em": time.strftime("%Y-%m-%d %H:%M"),
    "fonte": "Dados Abertos do Ministério do Turismo — https://dados.turismo.gov.br",
    "conjuntos": [c[0] for c in CONJUNTOS],
}, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"\nConjuntos coletados: {len(R)} de {len(CONJUNTOS)}")
print(f"Gravado em: {BASE}")
