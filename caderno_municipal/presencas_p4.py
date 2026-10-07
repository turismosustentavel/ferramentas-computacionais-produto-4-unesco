# -*- coding: utf-8 -*-
"""
O que o visitante encontra e o que nao encontra.

As fichas de campo registram, alem das notas de 1 a 5, uma longa lista de
itens de sim/nao: existe CAT? ha piso tatil? o ponto de onibus informa o
itinerario? Este modulo reune esses itens numa grade item x ponto, que mostra
o que falta em cada ponto e o que falta em TODOS os pontos.

Cada formulario (Geral, Rodoviaria, Aeroporto, Aduana) nomeia os itens a sua
maneira. `TEMAS` reune os nomes equivalentes sob uma linha so; o que o
formulario daquele ponto nao pergunta fica em branco, e nao se confunde com
ausencia.
"""
from __future__ import annotations

import re
import unicodedata

# ── vocabulario comum ───────────────────────────────────────────────────────
# (rótulo da linha, [nomes que a alimentam, como vêm do formulário])

CHEGADA = [
    ("Recepção e informação ao visitante", [
        ("Centro de Atendimento ao Turista", ["cat"]),
        ("Informações turísticas", ["informações turísticas",
                                    "informações turísticas (placas)"]),
        ("Balcão de informações", ["balcão de informações"]),
        ("Indicação dos atrativos", [
            "indicação dos principais atrativos turísticos"]),
        ("Mapas", ["mapas", "mapa de pedestres"]),
        ("QR code", ["qr code"]),
        ("Wi-Fi público", ["wi-fi público"]),
        ("Telefonia móvel", ["telefonia móvel",
                             "telefonia móvel disponível"]),
    ]),
    ("Acessibilidade", [
        ("Rampa", ["rampas", "rampa de acesso"]),
        ("Piso tátil", ["piso tátil"]),
        ("Sanitário acessível", ["sanitário acessível"]),
        ("Vagas reservadas para PCD", [
            "vagas reservadas para pcd",
            "vagas reservadas para pcd no estacionamento",
            "vagas reservadas para pcd no saguão de espera"]),
        ("Atendimento prioritário", [
            "atendimento prioritário sinalizado",
            "guichê de atendimento com acessibilidade aparente/"
            "atendimento prioritário (receita e polícia)"]),
    ]),
    ("Ligação com o transporte local", [
        ("Linhas de ônibus urbano", [
            "linhas públicas de ônibus", "integração com transporte urbano",
            "integração com terminal de transporte urbano "
            "(há pontos/linhas urbanas)"]),
        ("Ponto de táxi", ["ponto de táxi"]),
        ("Aplicativo de transporte", ["área para app de transporte"]),
        ("Estacionamento para ônibus de turismo", [
            "estacionamento para ônibus de turismo",
            "estacionamento para ônibus/veículos de turismo"]),
        ("Integração com países vizinhos", [
            "integração com países vizinhos"]),
    ]),
]

# A aduana não é um terminal como os outros. O que ela oferece — ou deixa de
# oferecer — a quem atravessa a fronteira não aparece em nenhuma outra ficha:
# a placa que diz onde é a fila de saída, a informação sobre que documento
# levar, a separação entre quem vai a pé e quem vai de carro.
ADUANA = [
    ("Orientação de quem atravessa", [
        # O CAT é item do Termo de Referência e por isso consta de todos os
        # vocabulários de ponto de chegada (CHEGADA, ADUANA, RODOVIARIA,
        # AEROPORTO), ainda que repita a linha da grade geral de terminais.
        ("Centro de Atendimento ao Turista", ["cat"]),
        ("Sinalização direcional", ["sinalização direcional (indicação de "
                                    "locais)"]),
        ("Placas dos setores da aduana", [
            "placas indicando os setores da aduana"]),
        ("Placas de entrada e saída", [
            "placas indicando fluxos de entrada/saída"]),
        ("Placas de orientação", ["placas de orientação"]),
        ("Horário e funcionamento", [
            "sinalização institucional (horários, funcionamento)"]),
        ("Documentação necessária", [
            "informações sobre documentação necessária"]),
    ]),
    ("Pedestres e veículos", [
        ("Separação entre pedestres e veículos", [
            "separação entre pedestres e veículos"]),
        ("Estacionamento para veículos leves", [
            "estacionamento para veículos leves"]),
        ("Estacionamento para ônibus de turismo", [
            "estacionamento para ônibus de turismo",
            "estacionamento para ônibus/veículos de turismo"]),
        ("Lixeiras", ["lixeiras"]),
    ]),
    ("Controle e segurança", [
        ("Controle de acesso", ["controle de acesso"]),
        ("Policiamento visível", ["policiamento visível"]),
        ("Câmeras", ["câmeras"]),
        ("Cercamento ou barreira física", [
            "cercamento/barreiras físicas"]),
        ("Visibilidade do ambiente", [
            "visibilidade do ambiente (permeabilidade visual)"]),
        ("Iluminação adequada", ["iluminação adequada"]),
    ]),
]

# O que só a ficha da rodoviária pergunta. O terminal é onde o passageiro
# espera, compra e se orienta, e nada disso aparece nas outras fichas.
RODOVIARIA = [
    ("Orientação de quem embarca", [
        ("Centro de Atendimento ao Turista", ["cat"]),
        ("Placas de orientação interna", ["placas de orientação interna"]),
        ("Painéis de partidas e chegadas", [
            "painéis eletrônicos de partidas e chegadas"]),
        ("Identificação das plataformas", [
            "identificação das plataformas"]),
        ("Informações sobre horários", ["informações sobre horários"]),
        ("Informações sobre linhas", ["informações sobre linhas"]),
    ]),
    ("Comprar e despachar", [
        ("Guichês de vendas", ["guichês de vendas"]),
        ("Autoatendimento de passagens", ["autoatendimento"]),
        ("Guarda-volumes", ["guarda-volumes"]),
    ]),
    ("Esperar", [
        ("Cobertura na área de espera", ["cobertura (área de espera)"]),
        ("Proteção climática", ["proteção climática"]),
        ("Banheiros", ["banheiros"]),
        ("Bebedouro", ["bebedouro", "bebedouros"]),
        ("Fraldário", ["fraldário"]),
        ("Lixeiras na área de espera", ["lixeiras (área de espera)"]),
        ("Lixeiras", ["lixeiras"]),
    ]),
    ("Comércio e serviços", [
        ("Alimentação", ["alimentação"]),
        ("Loja de conveniência", ["loja de conveniência"]),
        ("Loja de souvenirs", ["loja de souvenirs"]),
        ("Caixa eletrônico", ["caixa eletrônico"]),
    ]),
    ("Acesso e vigilância", [
        ("Área de embarque e desembarque", [
            "área de embarque e desembarque"]),
        ("Estacionamento para automóveis", [
            "estacionamento para automóveis"]),
        ("Câmeras", ["câmeras"]),
        ("Vigilância visível", ["vigilância/segurança visível"]),
    ]),
]

# O que só a ficha do aeroporto pergunta.
AEROPORTO = [
    ("Orientação de quem embarca", [
        ("Placas de orientação interna", ["placas de orientação interna"]),
        ("Painéis de partidas e chegadas", [
            "painéis eletrônicos de partidas e chegadas"]),
        ("Identificação dos portões", ["identificação dos portões"]),
        ("Informações sobre horários", ["informações sobre horários"]),
    ]),
    ("Embarque", [
        ("Autoatendimento de check-in", ["autoatendimento (check-in)"]),
        ("Área de embarque e desembarque", [
            "área de embarque/desembarque"]),
        ("Área para excursões e grupos", [
            "área destinada ao embarque de excursões e grupos"]),
        ("Controle de acesso à área restrita", [
            "controle de acesso a áreas restritas/área de embarque"]),
        ("Voos internacionais", ["voos internacionais"]),
    ]),
    ("Esperar", [
        ("Cobertura na área de espera", [
            "cobertura (área de espera antes da sala de embarque)"]),
        ("Proteção climática", ["proteção climática"]),
        ("Climatização", ["ventilação/climatização"]),
        ("Banheiros", ["banheiros"]),
        ("Bebedouros", ["bebedouros", "bebedouro"]),
        ("Fraldário", ["fraldário"]),
        ("Lixeiras na área de espera", ["lixeiras (área de espera)"]),
        ("Lixeiras", ["lixeiras"]),
    ]),
    ("Comércio e serviços", [
        ("Alimentação", ["alimentação"]),
        ("Loja de souvenir ou conveniência", [
            "loja de souvenir/conveniência"]),
        ("Caixa eletrônico", ["caixa eletrônico"]),
        ("Locadora de veículos", ["locadora de veículos"]),
        ("Serviço de câmbio", ["serviço de câmbio"]),
        ("Guarda-volumes", ["guarda-volumes"]),
    ]),
    ("Recepção do visitante", [
        ("Centro de Atendimento ao Turista", ["cat"]),
        ("Área para receptivos turísticos", [
            "área para receptivos turísticos"]),
        ("Sinalização para receptivos", [
            "sinalização para receptivos turísticos"]),
    ]),
    ("Circular dentro do terminal", [
        ("Elevador", ["elevador"]),
        ("Escada rolante", ["escada rolante"]),
        ("Estacionamento para automóveis", [
            "estacionamento para automóveis"]),
    ]),
    ("Vigilância", [
        ("Câmeras", ["câmeras"]),
        ("Vigilância visível", ["vigilância/segurança (pessoas visíveis)"]),
        ("Permeabilidade visual", ["permeabilidade visual"]),
    ]),
]

INTERNA = [
    ("A via e quem anda a pé", [
        ("Calçada", ["calçada"]),
        ("Rampa", ["rampa"]),
        ("Piso tátil", ["piso tátil"]),
        ("Faixa livre na calçada", ["faixa livre"]),
        ("Sinalização para pedestres", ["sinalização para pedestres"]),
        ("Iluminação para pedestres", ["iluminação para pedestres"]),
        ("Semáforo sonoro", ["semáforo sonoro"]),
        ("Acostamento", ["acostamento"]),
        ("Iluminação da via", ["iluminação"]),
        ("Ciclovia", ["ciclovia"]),
    ]),
    ("Transporte e informação", [
        ("Sinalização turística", ["sinalização turística"]),
        ("Ponto de ônibus", ["ponto de ônibus"]),
        ("Cobertura no ponto", ["cobertura (ponto de ônibus)"]),
        ("Assento no ponto", ["assento (ponto de ônibus)"]),
        ("Proteção lateral no ponto", ["proteção lateral (ponto de ônibus)"]),
        ("Sinalização no ponto", ["sinalização (ponto de ônibus)"]),
        ("Itinerário informado no ponto", [
            "informação de deslocamento (ponto de ônibus)"]),
        ("Ponto de táxi", ["ponto de táxi"]),
    ]),
]


def _chave(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore")
    return re.sub(r"\s+", " ", s.decode().lower()).strip()


def grade(fichas: dict, temas, numeros: list[int]) -> dict:
    """Monta a grade item × ponto.

    Devolve {"linhas": [(tema, rótulo, [estado por ponto])], ...} em que o
    estado é True (existe), False (não existe) ou None (o formulário daquele
    ponto não pergunta pelo item).
    """
    por_ponto = {}
    for ordem, f in fichas.items():
        n = int(re.search(r"(\d+)", str(ordem)).group(1))
        por_ponto[n] = {_chave(nome): bool(tem)
                        for nome, tem in f.get("presencas", [])}

    linhas = []
    for tema, itens in temas:
        for rotulo, nomes in itens:
            chaves = [_chave(x) for x in nomes]
            estados = []
            for n in numeros:
                achados = [por_ponto.get(n, {})[c] for c in chaves
                           if c in por_ponto.get(n, {})]
                # varios nomes para a mesma linha: basta um "sim"
                estados.append(any(achados) if achados else None)
            if any(e is not None for e in estados):
                linhas.append((tema, rotulo, estados))
    return {"linhas": linhas, "numeros": numeros}
