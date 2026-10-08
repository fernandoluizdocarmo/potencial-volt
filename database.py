import sqlite3
import os

# Compatibilidade com ambiente local e Vercel (onde apenas /tmp tem permissão de escrita)
if os.environ.get('VERCEL'):
    DB_PATH = '/tmp/orcamentos_eletrica.db'
    # Se o banco local já existir no projeto, copia para /tmp na primeira execução
    _local_db = os.path.join(os.path.dirname(__file__), 'orcamentos_eletrica.db')
    if os.path.exists(_local_db) and not os.path.exists(DB_PATH):
        try:
            import shutil
            shutil.copy2(_local_db, DB_PATH)
        except Exception:
            pass
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), 'orcamentos_eletrica.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Tabelas
    cur.execute('''
    CREATE TABLE IF NOT EXISTS configuracoes (
        chave TEXT PRIMARY KEY,
        valor TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS regioes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        descricao TEXT,
        taxa_deslocamento REAL DEFAULT 0.0,
        multiplicador REAL DEFAULT 1.0,
        ativo INTEGER DEFAULT 1
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS servicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        categoria TEXT DEFAULT 'Geral',
        unidade TEXT DEFAULT 'unidade',
        preco_base REAL NOT NULL,
        descricao TEXT,
        ativo INTEGER DEFAULT 1
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS precos_regiao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        servico_id INTEGER NOT NULL,
        regiao_id INTEGER NOT NULL,
        preco REAL NOT NULL,
        FOREIGN KEY (servico_id) REFERENCES servicos(id) ON DELETE CASCADE,
        FOREIGN KEY (regiao_id) REFERENCES regioes(id) ON DELETE CASCADE,
        UNIQUE (servico_id, regiao_id)
    )
    ''')

    # Tabela de Deslocamento entre Regiões (Origem -> Destino)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS rotas_deslocamento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        origem_id INTEGER NOT NULL,
        destino_id INTEGER NOT NULL,
        valor REAL NOT NULL,
        FOREIGN KEY (origem_id) REFERENCES regioes(id) ON DELETE CASCADE,
        FOREIGN KEY (destino_id) REFERENCES regioes(id) ON DELETE CASCADE,
        UNIQUE (origem_id, destino_id)
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS orcamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        cliente_nome TEXT NOT NULL,
        cliente_telefone TEXT,
        cliente_email TEXT,
        cliente_endereco TEXT,
        cliente_cidade TEXT,
        regiao_origem_id INTEGER,
        regiao_origem_nome TEXT,
        regiao_destino_id INTEGER,
        regiao_destino_nome TEXT,
        regiao_id INTEGER,
        regiao_nome TEXT,
        data_criacao TEXT NOT NULL,
        validade_dias INTEGER DEFAULT 15,
        taxa_deslocamento REAL DEFAULT 0.0,
        desconto REAL DEFAULT 0.0,
        total_servicos REAL DEFAULT 0.0,
        total_materiais REAL DEFAULT 0.0,
        total_geral REAL DEFAULT 0.0,
        materiais_modo TEXT DEFAULT 'cliente',
        forma_pagamento TEXT,
        garantia TEXT,
        prazo_execucao TEXT,
        observacoes TEXT,
        status TEXT DEFAULT 'Pendente'
    )
    ''')

    # Migração segura para colunas novas em orcamentos se já existia a tabela
    cur.execute("PRAGMA table_info(orcamentos)")
    colunas_orc = [col[1] for col in cur.fetchall()]
    novas_colunas = [
        ('regiao_origem_id', 'INTEGER'),
        ('regiao_origem_nome', 'TEXT'),
        ('regiao_destino_id', 'INTEGER'),
        ('regiao_destino_nome', 'TEXT')
    ]
    for col_nome, col_tipo in novas_colunas:
        if col_nome not in colunas_orc:
            try:
                cur.execute(f"ALTER TABLE orcamentos ADD COLUMN {col_nome} {col_tipo}")
            except Exception:
                pass

    cur.execute('''
    CREATE TABLE IF NOT EXISTS orcamento_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        orcamento_id INTEGER NOT NULL,
        servico_id INTEGER,
        descricao TEXT NOT NULL,
        unidade TEXT DEFAULT 'unidade',
        quantidade REAL NOT NULL,
        preco_unitario REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE CASCADE
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS orcamento_materiais (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        orcamento_id INTEGER NOT NULL,
        descricao TEXT NOT NULL,
        unidade TEXT DEFAULT 'un',
        quantidade REAL NOT NULL,
        preco_unitario REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE CASCADE
    )
    ''')

    conn.commit()

    # Inserir configurações padrão se não existirem
    configs_padrao = {
        'empresa_nome': 'Potencial Volt',
        'empresa_slogan': 'Instalações, Manutenções & Laudos Elétricos',
        'responsavel_nome': 'Fernando Carmo',
        'telefone': '(31) 99999-9999',
        'email': 'contato@potencialvolt.com.br',
        'chave_pix': 'contato@potencialvolt.com.br (E-mail)',
        'cidade_sede': 'Belo Horizonte / Vetor Norte - MG',
        'cidade_origem_padrao': 'Belo Horizonte (BH)',
        'garantia_padrao': '90 dias para serviços executados conforme normas NBR-5410.',
        'forma_pagamento_padrao': '50% de entrada na aprovação e 50% na conclusão (PIX, Dinheiro ou Cartão em até 12x)'
    }
    for k, v in configs_padrao.items():
        cur.execute('INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?)', (k, v))

    # Inserir as 5 Cidades Iniciais se tabela regioes estiver vazia
    cur.execute('SELECT COUNT(*) FROM regioes')
    if cur.fetchone()[0] == 0:
        cidades_mg = [
            ('Belo Horizonte (BH)', 'Atendimento em BH: Centro, Pampulha, Venda Nova, Barreiro e todas as regiões', 0.0, 1.0),
            ('Vespasiano', 'Atendimento em Vespasiano / Vetor Norte / MG-010', 25.0, 1.0),
            ('São José da Lapa', 'Atendimento em São José da Lapa e bairros vizinhos', 30.0, 1.0),
            ('Lagoa Santa', 'Atendimento em Lagoa Santa, condomínios e região', 40.0, 1.05),
            ('Pedro Leopoldo', 'Atendimento em Pedro Leopoldo e distritos', 45.0, 1.05),
        ]
        cur.executemany(
            'INSERT INTO regioes (nome, descricao, taxa_deslocamento, multiplicador) VALUES (?, ?, ?, ?)',
            cidades_mg
        )

    # Inserir Serviços Iniciais (baseados na planilha existente) se vazio
    cur.execute('SELECT COUNT(*) FROM servicos')
    if cur.fetchone()[0] == 0:
        servicos_iniciais = [
            ('Troca de Disjuntores monofásico / bifásico', 'Quadro de Distribuição', 'unidade', 60.0, 'Substituição e aperto de disjuntores mono ou bifásicos no quadro elétrico'),
            ('Troca de Disjuntores trifásico', 'Quadro de Distribuição', 'unidade', 90.0, 'Substituição de disjuntor trifásico no quadro elétrico geral ou secundário'),
            ('Refazer montagem do quadro elétrico (QDC)', 'Quadro de Distribuição', 'serviço', 250.0, 'Reorganização de barramentos, identificação de circuitos e montagem completa'),
            ('Instalação de IDR / DPS no quadro', 'Quadro de Distribuição', 'unidade', 120.0, 'Instalação de Dispositivo DR e Protetores de Surto para proteção contra choques e raios'),
            ('Instalação iluminação de jardim', 'Iluminação', 'unidade', 50.0, 'Fixação e ligação de luminária/espeto de jardim'),
            ('Refletor de Jardim', 'Iluminação', 'unidade', 80.0, 'Instalação e direcionamento de refletor de LED externo'),
            ('Instalação luminária de emergência simples', 'Iluminação', 'unidade', 90.0, 'Fixação e alimentação de luminária de emergência autônoma'),
            ('Troca de lâmpadas', 'Iluminação', 'unidade', 30.0, 'Substituição de lâmpada em teto ou arandela'),
            ('Instalação ou troca interruptor', 'Tomadas e Interruptores', 'unidade', 60.0, 'Substituição ou ligação de módulo interruptor simples, paralelo ou intermediário'),
            ('Troca de tomada', 'Tomadas e Interruptores', 'unidade', 30.0, 'Substituição de módulo de tomada padrão NBR 14136 10A/20A'),
            ('Novo ponto de tomada (sem quebrar parede)', 'Tomadas e Interruptores', 'ponto', 70.0, 'Passagem de fiação em eletroduto existente ou canaleta aparente'),
            ('Novo ponto de tomada (com quebra/embutido)', 'Tomadas e Interruptores', 'ponto', 130.0, 'Abertura de canaleta, chumbamento de conduíte, fiação e fechamento'),
            ('Instalação sensor de presença', 'Automação & Sensores', 'unidade', 50.0, 'Ligação e ajuste de temporização/sensibilidade de sensor'),
            ('Instalação de Ventilador de Teto / Lustre', 'Ventilação & Lustres', 'unidade', 90.0, 'Montagem completa, fixação estrutural e ligação elétrica com chave de controle'),
            ('Instalação Chuveiro padrão', 'Chuveiros & Aquecimento', 'unidade', 90.0, 'Fixação, vedação e conexão elétrica segura com conector adequado'),
            ('Troca de resistência de Chuveiro', 'Chuveiros & Aquecimento', 'unidade', 80.0, 'Desmontagem, substituição de resistência e teste de aquecimento'),
            ('Troca do cabeamento do chuveiro', 'Chuveiros & Aquecimento', 'serviço', 150.0, 'Passagem de fiação dimensionada (6mm² ou 10mm²) do quadro até o chuveiro'),
            ('Instalação ou troca torneira elétrica', 'Chuveiros & Aquecimento', 'unidade', 110.0, 'Instalação hidráulica e conexão elétrica dedicada'),
            ('Troca de Cabeamento', 'Infraestrutura', 'metro', 3.0, 'Passagem e enfiação de cabos por metro linear em tubulação'),
            ('Instalação completa residencial (até 70m²)', 'Instalação Completa', 'residência', 3000.0, 'Passagem de toda fiação, montagem de quadro, tomadas, interruptores e luminárias'),
            ('Instalação completa residencial (70m² a 150m²)', 'Instalação Completa', 'residência', 4500.0, 'Instalação elétrica total residencial de médio porte'),
            ('Instalação completa residencial (acima de 150m²)', 'Instalação Completa', 'residência', 6500.0, 'Instalação elétrica total residencial de grande porte'),
            ('Ponto dedicado para Ar Condicionado', 'Climatização', 'ponto', 140.0, 'Circuito independente do quadro até a condensadora/evaporadora com disjuntor dedicado'),
            ('Visita Técnica / Avaliação Diagnóstica', 'Diagnóstico & Laudos', 'visita', 100.0, 'Vistoria presencial no local com testes de continuidade, tensão e diagnóstico de falhas')
        ]
        cur.executemany(
            'INSERT INTO servicos (nome, categoria, unidade, preco_base, descricao) VALUES (?, ?, ?, ?, ?)',
            servicos_iniciais
        )

    # Preencher a tabela de precos_regiao se necessário
    cur.execute('SELECT COUNT(*) FROM precos_regiao')
    if cur.fetchone()[0] == 0:
        cur.execute('SELECT id, preco_base FROM servicos WHERE ativo = 1')
        todos_servicos = cur.fetchall()

        cur.execute('SELECT id, multiplicador FROM regioes WHERE ativo = 1')
        todas_regioes = cur.fetchall()

        for serv in todos_servicos:
            s_id = serv['id']
            preco_base = serv['preco_base']
            for reg in todas_regioes:
                r_id = reg['id']
                mult = reg['multiplicador']
                preco_calculado = round(preco_base * mult, 2)
                cur.execute(
                    'INSERT OR IGNORE INTO precos_regiao (servico_id, regiao_id, preco) VALUES (?, ?, ?)',
                    (s_id, r_id, preco_calculado)
                )

    # Preencher rotas de deslocamento entre as cidades
    popular_rotas_padrao(cur)

    conn.commit()
    conn.close()


def popular_rotas_padrao(cur):
    """
    Popula ou atualiza as taxas de deslocamento entre as cidades de MG:
    BH, Vespasiano, São José da Lapa, Lagoa Santa, Pedro Leopoldo.
    """
    cur.execute('SELECT id, nome FROM regioes WHERE ativo = 1')
    regioes_map = {row['nome']: row['id'] for row in cur.fetchall()}

    # Matriz de deslocamentos realistas entre as cidades (em Reais)
    tabela_deslocamentos = {
        ('Belo Horizonte (BH)', 'Belo Horizonte (BH)'): 20.0,
        ('Belo Horizonte (BH)', 'Vespasiano'): 30.0,
        ('Belo Horizonte (BH)', 'São José da Lapa'): 35.0,
        ('Belo Horizonte (BH)', 'Lagoa Santa'): 45.0,
        ('Belo Horizonte (BH)', 'Pedro Leopoldo'): 50.0,

        ('Vespasiano', 'Vespasiano'): 20.0,
        ('Vespasiano', 'São José da Lapa'): 20.0,
        ('Vespasiano', 'Lagoa Santa'): 25.0,
        ('Vespasiano', 'Pedro Leopoldo'): 30.0,
        ('Vespasiano', 'Belo Horizonte (BH)'): 30.0,

        ('São José da Lapa', 'São José da Lapa'): 20.0,
        ('São José da Lapa', 'Vespasiano'): 20.0,
        ('São José da Lapa', 'Lagoa Santa'): 30.0,
        ('São José da Lapa', 'Pedro Leopoldo'): 25.0,
        ('São José da Lapa', 'Belo Horizonte (BH)'): 35.0,

        ('Lagoa Santa', 'Lagoa Santa'): 20.0,
        ('Lagoa Santa', 'Vespasiano'): 25.0,
        ('Lagoa Santa', 'São José da Lapa'): 30.0,
        ('Lagoa Santa', 'Pedro Leopoldo'): 35.0,
        ('Lagoa Santa', 'Belo Horizonte (BH)'): 45.0,

        ('Pedro Leopoldo', 'Pedro Leopoldo'): 20.0,
        ('Pedro Leopoldo', 'São José da Lapa'): 25.0,
        ('Pedro Leopoldo', 'Vespasiano'): 30.0,
        ('Pedro Leopoldo', 'Lagoa Santa'): 35.0,
        ('Pedro Leopoldo', 'Belo Horizonte (BH)'): 50.0,
    }

    for (cid_origem, cid_destino), valor in tabela_deslocamentos.items():
        if cid_origem in regioes_map and cid_destino in regioes_map:
            orig_id = regioes_map[cid_origem]
            dest_id = regioes_map[cid_destino]
            cur.execute('''
                INSERT INTO rotas_deslocamento (origem_id, destino_id, valor)
                VALUES (?, ?, ?)
                ON CONFLICT(origem_id, destino_id) DO UPDATE SET valor = excluded.valor
            ''', (orig_id, dest_id, valor))

if __name__ == '__main__':
    init_db()
    print("Banco de dados inicializado com sucesso!")
