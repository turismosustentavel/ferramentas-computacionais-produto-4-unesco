# -*- coding: utf-8 -*-
"""
================================================================================
PROJETO UNESCO UNES 2369/2025 | ITAIPU PARQUETEC - TS.DTUR
PRODUTO 4: DIAGNÓSTICO REGIONAL DE INFRAESTRUTURA, MOBILIDADE E CONECTIVIDADE
================================================================================
MÓDULO AUXILIAR: _caminhos.py
--------------------------------------------------------------------------------
O QUE FAZ:
    Define, em um único lugar, a raiz da árvore de dados usada por todos os
    scripts da pasta `regional/`. Nenhum script contém caminho absoluto: todos
    partem das constantes abaixo.

RAIZ DOS DADOS:
    Lida da variável de ambiente P4_DADOS. Sem ela, a raiz é a pasta `dados/`
    na raiz do repositório. A árvore abaixo da raiz reproduz a pasta do
    convênio:

        <P4_DADOS>/
            Entregas/Produto 4/                    -> ENTREGAS
                produção/                          -> PRODUCAO
                    05_telemetria_velocidades_reais_tomtom/
                    08_transporte_coletivo_rodoviarias_clickbus/
                    09_aviacao_rotas_e_aeroportos_anac/
                    12_portas_entrada_terrestres_oficiais_shp/
                    13_portas_federais_18_pontos_shp/
                    14_portas_estaduais_30_pontos_shp/
                    15_portas_vicinais_nao_pavimentadas_osm_shp/
            Levantamentos e Análises/Produto 4/    -> ACERVO

    O conteúdo esperado em cada pasta está descrito em `regional/README.md`.

USO NOS SCRIPTS:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from _caminhos import PRODUCAO

VARIÁVEIS DE AMBIENTE:
    P4_DADOS  (opcional) pasta raiz dos dados.
================================================================================
"""
import os
from pathlib import Path

RAIZ = Path(os.environ.get("P4_DADOS")
            or Path(__file__).resolve().parents[1] / "dados")

# Pasta de entregas do Produto 4 (contém a pasta "produção").
ENTREGAS = RAIZ / "Entregas" / "Produto 4"

# Pasta de produção: camadas de entrada, saídas intermediárias e saídas finais.
PRODUCAO = ENTREGAS / "produção"

# Acervo de levantamentos do Produto 4 (não usado diretamente pelos scripts
# regionais; exposto para manter a mesma árvore dos demais conjuntos).
ACERVO = RAIZ / "Levantamentos e Análises" / "Produto 4"
