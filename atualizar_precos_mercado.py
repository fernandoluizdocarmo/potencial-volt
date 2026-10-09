"""
ATUALIZADOR DE PRECOS DE MERCADO - Potencial Volt
===================================================
Precos baseados em pesquisa de mercado 2026 nos sites:
- GetNinjas.com.br
- Workfly.com.br
- Habitissimo.com.br
- Precisodeumprofissional.com.br
- ChamaoPro.com.br

Regiao BH = preco base de mercado (mediana entre piso e teto)
Cidades da RMBH (Vespasiano, Sao Jose da Lapa) = BH + ~5%
Cidades mais distantes (Lagoa Santa, Pedro Leopoldo) = BH + ~10%

Todos os valores sao MAO DE OBRA apenas (sem materiais).
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'orcamentos_eletrica.db')

# ============================================================
# TABELA DE PRECOS DE MERCADO BH 2026 (mediana do mercado)
# IDs conforme banco: SELECT id, nome FROM servicos
# ============================================================
PRECOS_MERCADO_BH = {
    # id: (nome_para_referencia, preco_bh)
    1:  ("Troca de Disjuntores monofasico/bifasico",  110.0),   # mercado: R$99-249, mediana ~R$110
    2:  ("Troca de Disjuntores trifasico",            150.0),   # mercado: R$120-280, mediana ~R$150
    3:  ("Refazer montagem do quadro (QDC)",          650.0),   # mercado: R$500-1200, mediana ~R$650
    4:  ("Instalacao de IDR / DPS no quadro",         180.0),   # mercado: R$150-250, mediana ~R$180
    5:  ("Instalacao iluminacao de jardim",            80.0),   # mercado: R$70-130, mediana ~R$80
    6:  ("Refletor de Jardim",                        100.0),   # mercado: R$80-150, mediana ~R$100
    7:  ("Instalacao luminaria de emergencia",        120.0),   # mercado: R$100-180, mediana ~R$120
    8:  ("Troca de lampadas",                          50.0),   # mercado: R$40-80, mediana ~R$50
    9:  ("Instalacao ou troca interruptor",            90.0),   # mercado: R$60-160, mediana ~R$90
    10: ("Troca de tomada",                            90.0),   # mercado: R$80-180, mediana ~R$90
    11: ("Novo ponto tomada sem quebrar parede",      110.0),   # mercado: R$80-150, mediana ~R$110
    12: ("Novo ponto tomada com quebra/embutido",     200.0),   # mercado: R$150-280, mediana ~R$200
    13: ("Instalacao sensor de presenca",              90.0),   # mercado: R$70-140, mediana ~R$90
    14: ("Instalacao Ventilador de Teto / Lustre",   150.0),   # mercado: R$100-300, mediana ~R$150
    15: ("Instalacao Chuveiro padrao",                170.0),   # mercado: R$100-320, mediana ~R$170
    16: ("Troca de resistencia de Chuveiro",          100.0),   # mercado: R$80-160, mediana ~R$100
    17: ("Troca do cabeamento do chuveiro",           220.0),   # mercado: R$150-320, mediana ~R$220
    18: ("Instalacao ou troca torneira eletrica",     180.0),   # mercado: R$130-260, mediana ~R$180
    19: ("Troca de Cabeamento por metro",               8.0),   # mercado: R$6-12/metro, mediana ~R$8
    20: ("Instalacao completa residencial ate 70m2", 4500.0),   # mercado: R$3500-6000, mediana ~R$4500
    21: ("Instalacao completa 70m2 a 150m2",         7500.0),   # mercado: R$6000-10000, mediana ~R$7500
    22: ("Instalacao completa acima de 150m2",      11000.0),   # mercado: R$8000-15000+, mediana ~R$11000
    23: ("Ponto dedicado para Ar Condicionado",       200.0),   # mercado: R$150-300, mediana ~R$200
    24: ("Visita Tecnica / Avaliacao Diagnostica",    130.0),   # mercado: R$90-199, mediana ~R$130
}

# ============================================================
# MULTIPLICADORES POR CIDADE
# BH = 1.00 (referencia)
# Vespasiano e Sao Jose da Lapa: RMBH proxima, +5%
# Lagoa Santa e Pedro Leopoldo: mais distantes, +10%
# ============================================================
MULTIPLICADORES = {
    12: 1.00,   # Belo Horizonte (BH)
    13: 1.05,   # Vespasiano
    14: 1.05,   # Sao Jose da Lapa
    15: 1.10,   # Lagoa Santa
    16: 1.10,   # Pedro Leopoldo
}


def atualizar_precos():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    atualizados = 0
    erros = 0

    print("=" * 60)
    print("ATUALIZACAO DE PRECOS DE MERCADO 2026")
    print("Fonte: GetNinjas, Workfly, Habitissimo, PrecisodeumProfissional")
    print("=" * 60)

    for servico_id, (nome, preco_bh) in PRECOS_MERCADO_BH.items():
        for regiao_id, multiplicador in MULTIPLICADORES.items():
            preco_final = round(preco_bh * multiplicador, 2)

            try:
                cur.execute('''
                    INSERT INTO precos_regiao (servico_id, regiao_id, preco)
                    VALUES (?, ?, ?)
                    ON CONFLICT(servico_id, regiao_id) DO UPDATE SET preco = excluded.preco
                ''', (servico_id, regiao_id, preco_final))
                atualizados += 1
            except Exception as e:
                print(f"  ERRO servico {servico_id} regiao {regiao_id}: {e}")
                erros += 1

        # Atualiza tambem o preco_base do servico
        try:
            cur.execute('UPDATE servicos SET preco_base = ? WHERE id = ?', (preco_bh, servico_id))
        except Exception as e:
            print(f"  ERRO atualizando preco_base servico {servico_id}: {e}")

        print(f"  OK | {nome[:45]:<45} | BH: R$ {preco_bh:.2f}")

    conn.commit()
    conn.close()

    print()
    print(f"Total atualizados: {atualizados} registros em precos_regiao")
    print(f"Erros: {erros}")
    print()
    print("PRECOS POR CIDADE (baseados no mercado 2026):")
    print(f"  Belo Horizonte (BH): preco base (100%)")
    print(f"  Vespasiano:          +5% (RMBH proxima)")
    print(f"  Sao Jose da Lapa:    +5% (RMBH proxima)")
    print(f"  Lagoa Santa:         +10% (maior deslocamento)")
    print(f"  Pedro Leopoldo:      +10% (maior deslocamento)")


if __name__ == "__main__":
    atualizar_precos()
