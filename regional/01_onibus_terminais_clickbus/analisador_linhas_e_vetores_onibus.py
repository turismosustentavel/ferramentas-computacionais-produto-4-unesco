# -*- coding: utf-8 -*-
"""
================================================================================
PROJETO UNESCO UNES 2369/2025 | ITAIPU PARQUETEC - TS.DTUR
PRODUTO 4: DIAGNÓSTICO REGIONAL DE INFRAESTRUTURA, MOBILIDADE E CONECTIVIDADE
================================================================================
MÓDULO 01: TRANSPORTE RODOVIÁRIO COLETIVO E TERMINAIS
SCRIPT: analisador_linhas_e_vetores_onibus.py
--------------------------------------------------------------------------------
O QUE FAZ:
    Lê a planilha de bilhetagem do transporte rodoviário interestadual de
    passageiros (um registro por par origem-destino) e executa, em sequência:
      1) Panorama geral: soma de bilhetes; faturamento estimado como
         soma(media_valor_total x quantidade_bilhetes); tarifa média geral
         como faturamento estimado / total de bilhetes.
      2) Os dez pares origem-destino com mais bilhetes (impressos no terminal).
      3) Classificação de cada registro em relação à Faixa de Fronteira:
         origem e destino são considerados "na faixa" quando o nome
         normalizado (sem acento, maiúsculo) contém algum dos nomes da lista
         `cities_inside_ff`, escrita neste script. Classes: Intra-Faixa,
         Inbound (chegada de fora), Outbound (saída) e Externo / Trânsito.
      4) Marcação de rotas transfronteiriças: origem ou destino contém um dos
         nomes de cidades estrangeiras da lista `destinos_internacionais`.
      5) Exportação de um resumo por par origem-destino.

ENTRADAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/08_transporte_coletivo_rodoviarias_clickbus/
        cidades_fronteira_2025.xlsx
        Colunas usadas: ponto_origem_viagem, ponto_destino_viagem,
        quantidade_bilhetes, media_valor_total.
        Fonte: extrato de bilhetagem do transporte rodoviário interestadual
        de passageiros da ANTT (conjunto "Monitriip Bilhetes de Passagem"),
        filtrado para os municípios de interesse. Portal de dados abertos da
        ANTT: https://dados.antt.gov.br/

SAÍDAS (caminhos relativos a P4_DADOS):
    Entregas/Produto 4/produção/08_transporte_coletivo_rodoviarias_clickbus/
        resumo_analise_linhas_vetores_onibus.csv
        Uma linha por par origem-destino: bilhetes (soma), tarifa_media
        (média simples de media_valor_total) e tipo_fluxo (classe da etapa 3).
    Os demais resultados (panorama, pares mais movimentados, segmentação por
    tipo de fluxo e rotas transfronteiriças) são impressos no terminal.

VARIÁVEIS DE AMBIENTE:
    P4_DADOS  (opcional) raiz da árvore de dados; padrão: `dados/` na raiz
              do repositório.

COMO EXECUTAR:
    python regional/01_onibus_terminais_clickbus/analisador_linhas_e_vetores_onibus.py
================================================================================
"""

# ==============================================================================
# ETAPA 1: IMPORTAÇÃO DE PACOTES
# ==============================================================================
import os
import sys
import unicodedata
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _caminhos import PRODUCAO

sys.stdout.reconfigure(encoding='utf-8')

# ==============================================================================
# ETAPA 2: DIRETÓRIOS E CONSTANTES
# ==============================================================================
prod_out_dir = str(PRODUCAO)
bus_folder = os.path.join(prod_out_dir, "08_transporte_coletivo_rodoviarias_clickbus")
xlsx_path = os.path.join(bus_folder, "cidades_fronteira_2025.xlsx")

# Nomes normalizados (sem acento, maiúsculos) dos municípios tratados como
# situados na Faixa de Fronteira. A comparação é feita por substring.
cities_inside_ff = set([
    'FOZ DO IGUACU', 'CAMPO GRANDE', 'MEDIANEIRA', 'UMUARAMA', 'CASCAVEL',
    'MUNDO NOVO', 'GUAIRA', 'CAPANEMA', 'PONTA PORA', 'TOLEDO', 'MARECHAL CANDIDO RONDON',
    'PATO BRANCO', 'FRANCISCO BELTRAO', 'REALEZA', 'PARANAVAI', 'SANTO ANTONIO DO SUDOESTE',
    'CAMPO MOURAO', 'PALOTINA', 'BARRACAO', 'NOVA LONDRINA', 'PRANCHITA', 'PLANALTO',
    'DIAMANTE DO NORTE', 'CAPITAO LEONIDAS MARQUES', 'LOANDA', 'MARMELEIRO',
    'SANTA TEREZINHA DE ITAIPU', 'NOVA ANDRADINA', 'LARANJEIRAS DO SUL', 'PEROLA D\'OESTE',
    'AMPERE', 'SAO MIGUEL DO IGUACU', 'BRASILANDIA', 'ASSIS CHATEAUBRIAND', 'UBIRATA',
    'CHOPINZINHO', 'CORUMBA', 'TRES LAGOAS', 'CEU AZUL', 'TERRA ROXA', 'SANTA ISABEL DO IVAI',
    'CIANORTE', 'CLEVELANDIA', 'NAVIRAI', 'DOURADOS', 'MATELANDIA', 'MARIOPOLIS', 'PALMAS',
    'BONITO', 'PORTO MURTINHO', 'MIRANDA', 'BODOQUENA', 'BELA VISTA', 'PORTO RICO',
    'SETE QUEDAS', 'PARANHOS', 'CORONEL SAPUCAIA', 'AMAMBAI', 'JAPORA', 'ANASTACIO',
    'RIBAS DO RIO PARDO', 'IVINHEMA', 'SIDROLANDIA', 'MARACAJU', 'DEODAPOLIS', 'LINDOESTE',
    'CRUZEIRO DO OESTE', 'COLORADO', 'NOVA ESPERANCA', 'PLANALTINA DO PARANA', 'RENASCENCA',
    'AGUA CLARA', 'COXIM', 'RIO VERDE DE MATO GROSSO', 'SAO GABRIEL DO OESTE'
])

def normalize_text(text):
    """Remove acentos, '?' e hífens; devolve o texto em maiúsculas."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    return text.replace('?', '').replace('-', ' ').strip().upper()

# ==============================================================================
# ETAPA 3: PROCESSAMENTO
# ==============================================================================
def executar_analise_onibus():
    print("\n================================================================================")
    print(" ANÁLISE INTEGRADA DA MALHA DE ÔNIBUS REGULARES (PRODUTO 4)")
    print("================================================================================")

    if not os.path.exists(xlsx_path):
        print(f"Arquivo não encontrado: {xlsx_path}")
        return

    df = pd.read_excel(xlsx_path)
    total_bilhetes = df['quantidade_bilhetes'].sum()
    valor_total_estimado = (df['media_valor_total'] * df['quantidade_bilhetes']).sum()

    print(f"\n[1/4] PANORAMA GERAL DA BILHETAGEM:")
    print(f"  - Total de registros analisados: {len(df):,}")
    print(f"  - Total de bilhetes emitidos: {total_bilhetes:,}")
    print(f"  - Faturamento estimado: R$ {valor_total_estimado:,.2f}")
    print(f"  - Ticket médio geral: R$ {valor_total_estimado / total_bilhetes:.2f}")

    # 2. Pares origem-destino
    df['origem_norm'] = df['ponto_origem_viagem'].apply(normalize_text)
    df['destino_norm'] = df['ponto_destino_viagem'].apply(normalize_text)
    df['par_od'] = df['ponto_origem_viagem'] + " -> " + df['ponto_destino_viagem']

    print("\n[2/4] TOP 10 CORREDORES ORIGEM-DESTINO (OD) MAIS MOVIMENTADOS:")
    top_od = df.groupby('par_od').agg(
        total_bilhetes=('quantidade_bilhetes', 'sum'),
        tarifa_media=('media_valor_total', 'mean')
    ).sort_values(by='total_bilhetes', ascending=False).head(10)
    for idx, (pair, row) in enumerate(top_od.iterrows(), 1):
        print(f"  #{idx:02d} {pair[:45]:45s} | Bilhetes: {int(row['total_bilhetes']):>7,d} | Tarifa Média: R$ {row['tarifa_media']:>6.2f}")

    # 3. Classificação dentro / fora da Faixa de Fronteira (150 km)
    df['origem_in_ff'] = df['origem_norm'].apply(lambda x: any(c in x for c in cities_inside_ff))
    df['destino_in_ff'] = df['destino_norm'].apply(lambda x: any(c in x for c in cities_inside_ff))

    def classificar_fluxo(r):
        if r['origem_in_ff'] and r['destino_in_ff']:
            return "Intra-Faixa (Regional Interno)"
        elif not r['origem_in_ff'] and r['destino_in_ff']:
            return "Inbound (Chegada de Fora à Fronteira)"
        elif r['origem_in_ff'] and not r['destino_in_ff']:
            return "Outbound (Saída da Fronteira)"
        else:
            return "Externo / Trânsito"

    df['tipo_fluxo_fronteira'] = df.apply(classificar_fluxo, axis=1)

    print("\n[3/4] SEGMENTAÇÃO DE FLUXO NA FAIXA DE FRONTEIRA (150 KM):")
    fluxo_agg = df.groupby('tipo_fluxo_fronteira').agg(
        bilhetes=('quantidade_bilhetes', 'sum'),
        participacao=('quantidade_bilhetes', lambda x: (x.sum() / total_bilhetes) * 100)
    ).sort_values(by='bilhetes', ascending=False)
    print(fluxo_agg.to_string())

    # 4. Rotas transfronteiriças (origem ou destino em cidade estrangeira)
    destinos_internacionais = ['CIUDAD DEL ESTE', 'ASUNCION', 'PUERTO IGUAZU', 'BUENOS AIRES', 'SANTA CRUZ', 'CORONEL OVIEDO']
    df['is_transfronteirica'] = df['destino_norm'].apply(lambda x: any(d in x for d in destinos_internacionais)) | df['origem_norm'].apply(lambda x: any(d in x for d in destinos_internacionais))

    df_trans = df[df['is_transfronteirica']]
    print(f"\n[4/4] ROTAS TRANSFRONTEIRIÇAS IDENTIFICADAS: {len(df_trans)} registros")
    if len(df_trans) > 0:
        trans_agg = df_trans.groupby('par_od')['quantidade_bilhetes'].sum().sort_values(ascending=False).head(5)
        print(trans_agg.to_string())

    # 5. Exportação do resumo por par origem-destino
    out_csv = os.path.join(bus_folder, "resumo_analise_linhas_vetores_onibus.csv")
    df.groupby('par_od').agg(
        bilhetes=('quantidade_bilhetes', 'sum'),
        tarifa_media=('media_valor_total', 'mean'),
        tipo_fluxo=('tipo_fluxo_fronteira', 'first')
    ).to_csv(out_csv, encoding='utf-8')
    print(f"\n [OK] Resumo analítico exportado para: {out_csv}")

if __name__ == '__main__':
    executar_analise_onibus()
