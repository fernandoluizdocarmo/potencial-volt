"""
ROBO DE COTACAO E ATUALIZACAO AUTOMATICA DE MERCADO
===================================================
Potencial Volt - Minas Gerais (BH, RMBH, Vetor Norte)

Fontes consultadas:
1. IBGE / Banco Central (SGS Série 433) - Inflação Oficial Acumulada
2. Tabelas e faixas de cotação de serviços elétricos (GetNinjas, Workfly, Habitissimo)
3. Matriz regional de fatores de deslocamento e complexidade por cidade
"""

import os
import json
import sqlite3
import urllib.request
from datetime import datetime

# ============================================================
# MATRIZ BASE DE MERCADO (Referência BH 2026)
# ============================================================
PRECOS_MERCADO_REFERENCIA_BH = {
    1:  ("Troca de Disjuntores monofásico / bifásico", 110.0),
    2:  ("Troca de Disjuntores trifásico", 150.0),
    3:  ("Refazer montagem do quadro elétrico (QDC)", 650.0),
    4:  ("Instalação de IDR / DPS no quadro", 180.0),
    5:  ("Instalação iluminação de jardim", 80.0),
    6:  ("Refletor de Jardim", 100.0),
    7:  ("Instalação luminária de emergência simples", 120.0),
    8:  ("Troca de lâmpadas", 50.0),
    9:  ("Instalação ou troca interruptor", 90.0),
    10: ("Troca de tomada", 90.0),
    11: ("Novo ponto de tomada (sem quebrar parede)", 110.0),
    12: ("Novo ponto de tomada (com quebra/embutido)", 200.0),
    13: ("Instalação sensor de presença", 90.0),
    14: ("Instalação de Ventilador de Teto / Lustre", 150.0),
    15: ("Instalação Chuveiro padrão", 170.0),
    16: ("Troca de resistência de Chuveiro", 100.0),
    17: ("Troca do cabeamento do chuveiro", 220.0),
    18: ("Instalação ou troca torneira elétrica", 180.0),
    19: ("Troca de Cabeamento", 8.0),
    20: ("Instalação completa residencial (até 70m²)", 4500.0),
    21: ("Instalação completa residencial (70m² a 150m²)", 7500.0),
    22: ("Instalação completa residencial (acima de 150m²)", 11000.0),
    23: ("Ponto dedicado para Ar Condicionado", 200.0),
    24: ("Visita Técnica / Avaliação Diagnóstica", 130.0)
}

FATORES_REGIAO = {
    12: 1.00,  # Belo Horizonte (BH)
    13: 1.05,  # Vespasiano
    14: 1.05,  # São José da Lapa
    15: 1.10,  # Lagoa Santa
    16: 1.10   # Pedro Leopoldo
}


def obter_indice_inflacao_bcb():
    """Consulta a API oficial do Banco Central do Brasil para obter o IPCA mais recente."""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/1?formato=json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data and len(data) > 0:
                taxa = float(data[0].get('valor', '0'))
                data_ref = data[0].get('data', '')
                return {'sucesso': True, 'taxa': taxa, 'data': data_ref}
    except Exception as e:
        print(f"[Aviso] Falha ao consultar Banco Central: {e}")
    return {'sucesso': False, 'taxa': 0.0, 'data': datetime.now().strftime('%d/%m/%Y')}


def executar_robo_cotacao(conn, aplicar_inflacao=False, percentual_extra=0.0):
    """
    Executa a varredura e atualização de preços no banco de dados.
    """
    cur = conn.cursor()
    
    # 1. Obter inflação se solicitado
    info_bcb = obter_indice_inflacao_bcb()
    ajuste_inflacao = 1.0
    if aplicar_inflacao and info_bcb['sucesso'] and info_bcb['taxa'] > 0:
        ajuste_inflacao = 1.0 + (info_bcb['taxa'] / 100.0)

    # 2. Ajuste percentual manual (se houver)
    ajuste_extra = 1.0 + (percentual_extra / 100.0)
    
    multiplicador_total = ajuste_inflacao * ajuste_extra

    atualizados = 0

    # 3. Atualizar cada serviço e suas variações regionais
    for servico_id, (nome, preco_base_ref) in PRECOS_MERCADO_REFERENCIA_BH.items():
        novo_preco_base = round(preco_base_ref * multiplicador_total, 2)
        
        # Atualiza o preço base do serviço
        cur.execute('UPDATE servicos SET preco_base = ? WHERE id = ?', (novo_preco_base, servico_id))
        
        # Atualiza os preços para cada cidade
        for regiao_id, fator_cid in FATORES_REGIAO.items():
            preco_cidade = round(novo_preco_base * fator_cid, 2)
            cur.execute('''
                INSERT INTO precos_regiao (servico_id, regiao_id, preco)
                VALUES (?, ?, ?)
                ON CONFLICT(servico_id, regiao_id) DO UPDATE SET preco = excluded.preco
            ''', (servico_id, regiao_id, preco_cidade))
            atualizados += 1

    # 4. Registrar log da última cotação executada
    agora_str = datetime.now().strftime('%d/%m/%Y às %H:%M')
    cur.execute('''
        INSERT INTO configuracoes (chave, valor)
        VALUES ('ultima_cotacao_mercado', ?)
        ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
    ''', (agora_str,))

    conn.commit()

    return {
        'sucesso': True,
        'total_precos_atualizados': atualizados,
        'data_execucao': agora_str,
        'taxa_inflacao_detectada': info_bcb.get('taxa', 0.0),
        'mensagem': f"Preços de mercado sincronizados com sucesso em {agora_str}!"
    }
