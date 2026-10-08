import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from database import get_connection, init_db

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# Garante que o banco exista
init_db()

# ======================== ROTAS DE PÁGINAS ========================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/orcamento/imprimir/<int:orcamento_id>')
def imprimir_orcamento(orcamento_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM orcamentos WHERE id = ?', (orcamento_id,))
    orcamento = cur.fetchone()
    if not orcamento:
        conn.close()
        return "Orçamento não encontrado", 404

    cur.execute('SELECT * FROM orcamento_itens WHERE orcamento_id = ?', (orcamento_id,))
    itens = cur.fetchall()

    cur.execute('SELECT * FROM orcamento_materiais WHERE orcamento_id = ?', (orcamento_id,))
    materiais = cur.fetchall()

    cur.execute('SELECT chave, valor FROM configuracoes')
    configs = {row['chave']: row['valor'] for row in cur.fetchall()}

    conn.close()
    return render_template('orcamento_print.html', orcamento=orcamento, itens=itens, materiais=materiais, config=configs)


# ======================== ROTAS DA API ========================

@app.route('/api/configuracoes', methods=['GET', 'POST'])
def api_configuracoes():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        dados = request.get_json() or {}
        for k, v in dados.items():
            cur.execute('INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)', (k, str(v)))
        conn.commit()
        conn.close()
        return jsonify({'sucesso': True, 'mensagem': 'Configurações salvas com sucesso!'})

    cur.execute('SELECT chave, valor FROM configuracoes')
    configs = {row['chave']: row['valor'] for row in cur.fetchall()}
    conn.close()
    return jsonify(configs)


@app.route('/api/regioes', methods=['GET', 'POST'])
def api_regioes():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        dados = request.get_json() or {}
        nome = dados.get('nome', '').strip()
        descricao = dados.get('descricao', '').strip()
        taxa = float(dados.get('taxa_deslocamento', 0.0) or 0.0)
        multiplicador = float(dados.get('multiplicador', 1.0) or 1.0)

        if not nome:
            conn.close()
            return jsonify({'erro': 'Nome da região é obrigatório'}), 400

        try:
            cur.execute(
                'INSERT INTO regioes (nome, descricao, taxa_deslocamento, multiplicador) VALUES (?, ?, ?, ?)',
                (nome, descricao, taxa, multiplicador)
            )
            nova_regiao_id = cur.lastrowid

            # Gera os preços padrão para todos os serviços cadastrados para esta nova região
            cur.execute('SELECT id, preco_base FROM servicos WHERE ativo = 1')
            servicos = cur.fetchall()
            for s in servicos:
                preco_calc = round(s['preco_base'] * multiplicador, 2)
                cur.execute(
                    'INSERT OR IGNORE INTO precos_regiao (servico_id, regiao_id, preco) VALUES (?, ?, ?)',
                    (s['id'], nova_regiao_id, preco_calc)
                )

            conn.commit()
            conn.close()
            return jsonify({'sucesso': True, 'id': nova_regiao_id, 'mensagem': 'Região cadastrada com sucesso!'})
        except Exception as e:
            conn.close()
            return jsonify({'erro': f'Erro ao cadastrar região: {str(e)}'}), 400

    cur.execute('SELECT * FROM regioes WHERE ativo = 1 ORDER BY nome ASC')
    regioes = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(regioes)


@app.route('/api/regioes/<int:regiao_id>', methods=['PUT', 'DELETE'])
def api_regiao_detalhe(regiao_id):
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'DELETE':
        cur.execute('UPDATE regioes SET ativo = 0 WHERE id = ?', (regiao_id,))
        conn.commit()
        conn.close()
        return jsonify({'sucesso': True, 'mensagem': 'Região desativada com sucesso!'})

    dados = request.get_json() or {}
    nome = dados.get('nome', '').strip()
    descricao = dados.get('descricao', '').strip()
    taxa = float(dados.get('taxa_deslocamento', 0.0) or 0.0)
    multiplicador = float(dados.get('multiplicador', 1.0) or 1.0)

    cur.execute(
        'UPDATE regioes SET nome = ?, descricao = ?, taxa_deslocamento = ?, multiplicador = ? WHERE id = ?',
        (nome, descricao, taxa, multiplicador, regiao_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'sucesso': True, 'mensagem': 'Região atualizada com sucesso!'})


@app.route('/api/servicos', methods=['GET', 'POST'])
def api_servicos():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        dados = request.get_json() or {}
        nome = dados.get('nome', '').strip()
        categoria = dados.get('categoria', 'Geral').strip() or 'Geral'
        unidade = dados.get('unidade', 'unidade').strip() or 'unidade'
        preco_base = float(dados.get('preco_base', 0.0) or 0.0)
        descricao = dados.get('descricao', '').strip()

        if not nome:
            conn.close()
            return jsonify({'erro': 'Nome do serviço é obrigatório'}), 400

        try:
            cur.execute(
                'INSERT INTO servicos (nome, categoria, unidade, preco_base, descricao) VALUES (?, ?, ?, ?, ?)',
                (nome, categoria, unidade, preco_base, descricao)
            )
            novo_servico_id = cur.lastrowid

            # Gera preços para todas as regiões ativas
            cur.execute('SELECT id, multiplicador FROM regioes WHERE ativo = 1')
            regioes = cur.fetchall()
            for r in regioes:
                preco_regiao = round(preco_base * r['multiplicador'], 2)
                cur.execute(
                    'INSERT OR IGNORE INTO precos_regiao (servico_id, regiao_id, preco) VALUES (?, ?, ?)',
                    (novo_servico_id, r['id'], preco_regiao)
                )

            conn.commit()
            conn.close()
            return jsonify({'sucesso': True, 'id': novo_servico_id, 'mensagem': 'Serviço cadastrado com sucesso!'})
        except Exception as e:
            conn.close()
            return jsonify({'erro': f'Erro ao cadastrar serviço: {str(e)}'}), 400

    cur.execute('SELECT * FROM servicos WHERE ativo = 1 ORDER BY categoria ASC, nome ASC')
    servicos = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(servicos)


@app.route('/api/servicos/<int:servico_id>', methods=['PUT', 'DELETE'])
def api_servico_detalhe(servico_id):
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'DELETE':
        cur.execute('UPDATE servicos SET ativo = 0 WHERE id = ?', (servico_id,))
        conn.commit()
        conn.close()
        return jsonify({'sucesso': True, 'mensagem': 'Serviço desativado com sucesso!'})

    dados = request.get_json() or {}
    nome = dados.get('nome', '').strip()
    categoria = dados.get('categoria', 'Geral').strip()
    unidade = dados.get('unidade', 'unidade').strip()
    preco_base = float(dados.get('preco_base', 0.0) or 0.0)
    descricao = dados.get('descricao', '').strip()

    cur.execute(
        'UPDATE servicos SET nome = ?, categoria = ?, unidade = ?, preco_base = ?, descricao = ? WHERE id = ?',
        (nome, categoria, unidade, preco_base, descricao, servico_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'sucesso': True, 'mensagem': 'Serviço atualizado com sucesso!'})


@app.route('/api/precos/<int:regiao_id>')
def api_precos_por_regiao(regiao_id):
    """
    Retorna todos os serviços com o preço específico cadastrado para esta região informada.
    Se um preço não estiver explicitamente na tabela precos_regiao, calcula usando multiplicador da região.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Pega detalhes da região
    cur.execute('SELECT * FROM regioes WHERE id = ?', (regiao_id,))
    regiao = cur.fetchone()
    if not regiao:
        conn.close()
        return jsonify({'erro': 'Região não encontrada'}), 404

    mult = regiao['multiplicador'] or 1.0
    taxa_deslocamento = regiao['taxa_deslocamento'] or 0.0

    # Busca serviços e une com precos_regiao
    query = '''
    SELECT 
        s.id AS servico_id,
        s.nome,
        s.categoria,
        s.unidade,
        s.preco_base,
        s.descricao,
        COALESCE(pr.preco, ROUND(s.preco_base * ?, 2)) AS preco_regiao
    FROM servicos s
    LEFT JOIN precos_regiao pr ON pr.servico_id = s.id AND pr.regiao_id = ?
    WHERE s.ativo = 1
    ORDER BY s.categoria ASC, s.nome ASC
    '''
    cur.execute(query, (mult, regiao_id))
    servicos_precos = [dict(row) for row in cur.fetchall()]

    conn.close()
    return jsonify({
        'regiao': dict(regiao),
        'taxa_deslocamento': taxa_deslocamento,
        'servicos': servicos_precos
    })

@app.route('/api/calcular-deslocamento')
def api_calcular_deslocamento():
    origem_id = request.args.get('origem_id', type=int)
    destino_id = request.args.get('destino_id', type=int)

    if not origem_id or not destino_id:
        return jsonify({'erro': 'Origem e destino são obrigatórios'}), 400

    conn = get_connection()
    cur = conn.cursor()

    cur.execute('SELECT id, nome, taxa_deslocamento FROM regioes WHERE id = ?', (origem_id,))
    origem = cur.fetchone()
    cur.execute('SELECT id, nome, taxa_deslocamento FROM regioes WHERE id = ?', (destino_id,))
    destino = cur.fetchone()

    if not origem or not destino:
        conn.close()
        return jsonify({'erro': 'Região não encontrada'}), 404

    # Sempre busca na tabela (mesma cidade = R$20 conforme configurado no banco)
    cur.execute('''
        SELECT valor FROM rotas_deslocamento 
        WHERE (origem_id = ? AND destino_id = ?) OR (origem_id = ? AND destino_id = ?)
        LIMIT 1
    ''', (origem_id, destino_id, destino_id, origem_id))
    rota = cur.fetchone()
    if rota:
        valor = rota['valor']
    else:
        valor = 20.0 if origem_id == destino_id else (destino['taxa_deslocamento'] or 30.0)

    conn.close()
    return jsonify({
        'origem_id': origem['id'],
        'origem_nome': origem['nome'],
        'destino_id': destino['id'],
        'destino_nome': destino['nome'],
        'valor_deslocamento': float(valor)
    })


@app.route('/api/materiais-sugeridos', methods=['POST'])
def api_materiais_sugeridos():
    """
    Recebe uma lista de servico_ids e retorna os materiais/componentes
    tipicamente utilizados nesses serviços, com preços de mercado atuais em MG.
    """
    dados = request.get_json() or {}
    servico_ids = dados.get('servico_ids', [])

    # Catálogo completo de materiais por serviço (preços de mercado BH/MG 2024-2025)
    catalogo = {
        # ---- QUADRO DE DISTRIBUIÇÃO ----
        'Troca de Disjuntores': [
            {'descricao': 'Disjuntor monopolar 10A/16A/20A (Soprano/WEG)', 'unidade': 'un', 'preco': 18.00},
            {'descricao': 'Disjuntor monopolar 25A/32A', 'unidade': 'un', 'preco': 22.00},
            {'descricao': 'Disjuntor bipolar 25A/32A/40A', 'unidade': 'un', 'preco': 55.00},
            {'descricao': 'Disjuntor tripolar 25A/32A/40A', 'unidade': 'un', 'preco': 95.00},
        ],
        'Refazer montagem do quadro': [
            {'descricao': 'Barramento neutro/terra para QDC', 'unidade': 'un', 'preco': 35.00},
            {'descricao': 'Cabo flexivel 10mm² (rolo 10m)', 'unidade': 'rolo', 'preco': 65.00},
            {'descricao': 'Cabo flexivel 6mm² (rolo 10m)', 'unidade': 'rolo', 'preco': 40.00},
            {'descricao': 'Quadro de distribuicao 12/24 disjuntores', 'unidade': 'un', 'preco': 85.00},
            {'descricao': 'Disjuntor monopolar (pacote 10un)', 'unidade': 'pct', 'preco': 180.00},
        ],
        'IDR / DPS': [
            {'descricao': 'IDR (Interruptor Diferencial Residual) 25A/30mA', 'unidade': 'un', 'preco': 85.00},
            {'descricao': 'DPS (Dispositivo de Protecao contra Surtos) 275V', 'unidade': 'un', 'preco': 120.00},
            {'descricao': 'Cabo flexivel 4mm² (metro)', 'unidade': 'metro', 'preco': 4.50},
        ],
        # ---- CHUVEIRO & AQUECIMENTO ----
        'Chuveiro': [
            {'descricao': 'Cabo flexivel 4mm² (rolo 10m)', 'unidade': 'rolo', 'preco': 45.00},
            {'descricao': 'Cabo flexivel 6mm² (rolo 10m)', 'unidade': 'rolo', 'preco': 55.00},
            {'descricao': 'Disjuntor monopolar 32A', 'unidade': 'un', 'preco': 22.00},
            {'descricao': 'Disjuntor bipolar 40A', 'unidade': 'un', 'preco': 58.00},
            {'descricao': 'Eletroduto corrugado 3/4 (rolo 25m)', 'unidade': 'rolo', 'preco': 30.00},
            {'descricao': 'Luva e conector para eletroduto', 'unidade': 'kit', 'preco': 8.00},
        ],
        'Aquecedor / Boiler': [
            {'descricao': 'Cabo flexivel 6mm² (rolo 10m)', 'unidade': 'rolo', 'preco': 55.00},
            {'descricao': 'Disjuntor bipolar 40A/50A', 'unidade': 'un', 'preco': 65.00},
            {'descricao': 'Eletroduto rigido 3/4 (barra 3m)', 'unidade': 'barra', 'preco': 12.00},
        ],
        # ---- TOMADAS E INTERRUPTORES ----
        'Tomada': [
            {'descricao': 'Tomada 2P+T 10A padrão NBR (Pial/Tramontina)', 'unidade': 'un', 'preco': 12.00},
            {'descricao': 'Tomada 2P+T 20A padrao NBR (para ar-cond/chuveiro)', 'unidade': 'un', 'preco': 18.00},
            {'descricao': 'Caixa de embutir 4x4 (plastico)', 'unidade': 'un', 'preco': 3.50},
            {'descricao': 'Cabo flexivel 2,5mm² (metro)', 'unidade': 'metro', 'preco': 3.20},
            {'descricao': 'Eletroduto corrugado 3/4 (metro)', 'unidade': 'metro', 'preco': 1.80},
        ],
        'Interruptor': [
            {'descricao': 'Interruptor simples 10A (Pial/Tramontina)', 'unidade': 'un', 'preco': 10.00},
            {'descricao': 'Interruptor paralelo (three-way) 10A', 'unidade': 'un', 'preco': 14.00},
            {'descricao': 'Caixa de embutir 4x2 (plastico)', 'unidade': 'un', 'preco': 2.50},
            {'descricao': 'Cabo flexivel 1,5mm² (metro)', 'unidade': 'metro', 'preco': 2.20},
        ],
        # ---- ILUMINAÇÃO ----
        'Luminaria': [
            {'descricao': 'Luminaria de embutir LED 18W', 'unidade': 'un', 'preco': 45.00},
            {'descricao': 'Spot LED embutir 7W', 'unidade': 'un', 'preco': 22.00},
            {'descricao': 'Reatores/drivers LED', 'unidade': 'un', 'preco': 30.00},
            {'descricao': 'Cabo flexivel 1,5mm² (metro)', 'unidade': 'metro', 'preco': 2.20},
        ],
        'Lampada': [
            {'descricao': 'Lampada LED bulbo 9W/12W E27', 'unidade': 'un', 'preco': 12.00},
            {'descricao': 'Lampada LED tubular 20W T8', 'unidade': 'un', 'preco': 22.00},
        ],
        'Ventilador': [
            {'descricao': 'Cabo flexivel 1,5mm² (metro)', 'unidade': 'metro', 'preco': 2.20},
            {'descricao': 'Interruptor simples 10A', 'unidade': 'un', 'preco': 10.00},
            {'descricao': 'Suporte/gancho para ventilador de teto', 'unidade': 'un', 'preco': 25.00},
        ],
        # ---- INFRAESTRUTURA ----
        'Eletroduto': [
            {'descricao': 'Eletroduto corrugado 3/4 (rolo 25m)', 'unidade': 'rolo', 'preco': 30.00},
            {'descricao': 'Eletroduto rigido PVC 3/4 (barra 3m)', 'unidade': 'barra', 'preco': 12.00},
            {'descricao': 'Eletroduto rigido PVC 1 (barra 3m)', 'unidade': 'barra', 'preco': 16.00},
            {'descricao': 'Luvas, curvas e conectores PVC', 'unidade': 'kit', 'preco': 15.00},
        ],
        'Cabo / Passagem': [
            {'descricao': 'Cabo flexivel 1,5mm² (rolo 100m)', 'unidade': 'rolo', 'preco': 185.00},
            {'descricao': 'Cabo flexivel 2,5mm² (rolo 100m)', 'unidade': 'rolo', 'preco': 290.00},
            {'descricao': 'Cabo flexivel 4mm² (rolo 100m)', 'unidade': 'rolo', 'preco': 430.00},
            {'descricao': 'Cabo flexivel 6mm² (rolo 100m)', 'unidade': 'rolo', 'preco': 620.00},
            {'descricao': 'Fita isolante antichama 19mm', 'unidade': 'un', 'preco': 5.00},
        ],
        'Ar-condicionado': [
            {'descricao': 'Cabo flexivel 4mm² (rolo 10m)', 'unidade': 'rolo', 'preco': 45.00},
            {'descricao': 'Disjuntor bipolar 20A/25A', 'unidade': 'un', 'preco': 52.00},
            {'descricao': 'Tomada 2P+T 20A padrao NBR', 'unidade': 'un', 'preco': 18.00},
            {'descricao': 'Eletroduto corrugado 3/4 (rolo 25m)', 'unidade': 'rolo', 'preco': 30.00},
        ],
        # ---- SENSOR / AUTOMAÇÃO ----
        'Sensor': [
            {'descricao': 'Sensor de presenca de teto 360 graus', 'unidade': 'un', 'preco': 45.00},
            {'descricao': 'Sensor de presenca de parede 180 graus', 'unidade': 'un', 'preco': 38.00},
            {'descricao': 'Cabo flexivel 1,5mm² (metro)', 'unidade': 'metro', 'preco': 2.20},
        ],
    }

    # Busca nomes dos servicos selecionados no banco
    conn = get_connection()
    cur = conn.cursor()
    if servico_ids:
        placeholders = ','.join(['?' for _ in servico_ids])
        cur.execute(f'SELECT id, nome, categoria FROM servicos WHERE id IN ({placeholders})', servico_ids)
        servicos_sel = cur.fetchall()
    else:
        servicos_sel = []
    conn.close()

    # Mapeia serviços selecionados para materiais sugeridos
    materiais_sugeridos = {}
    for s in servicos_sel:
        nome_lower = s['nome'].lower()
        for chave, lista_mat in catalogo.items():
            if any(palavra in nome_lower for palavra in chave.lower().split()):
                for mat in lista_mat:
                    key = mat['descricao']
                    if key not in materiais_sugeridos:
                        materiais_sugeridos[key] = {**mat, 'quantidade': 1}

    # Se nenhum material específico foi encontrado, retorna lista geral básica
    if not materiais_sugeridos:
        materiais_sugeridos = {
            'Cabo flexivel 2,5mm² (metro)': {'descricao': 'Cabo flexivel 2,5mm² (metro)', 'unidade': 'metro', 'preco': 3.20, 'quantidade': 1},
            'Eletroduto corrugado 3/4 (rolo 25m)': {'descricao': 'Eletroduto corrugado 3/4 (rolo 25m)', 'unidade': 'rolo', 'preco': 30.00, 'quantidade': 1},
            'Fita isolante antichama 19mm': {'descricao': 'Fita isolante antichama 19mm', 'unidade': 'un', 'preco': 5.00, 'quantidade': 1},
        }

    return jsonify({
        'sucesso': True,
        'materiais': list(materiais_sugeridos.values())
    })


@app.route('/api/matriz-precos')
def api_matriz_precos():
    """
    Retorna todos os serviços e todas as regiões para montar a matriz completa de edição de preços.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM regioes WHERE ativo = 1 ORDER BY id ASC')
    regioes = [dict(r) for r in cur.fetchall()]

    cur.execute('SELECT * FROM servicos WHERE ativo = 1 ORDER BY categoria ASC, nome ASC')
    servicos = [dict(s) for s in cur.fetchall()]

    cur.execute('SELECT servico_id, regiao_id, preco FROM precos_regiao')
    precos_raw = cur.fetchall()

    # Mapear (servico_id, regiao_id) -> preco
    precos_map = {}
    for row in precos_raw:
        precos_map[f"{row['servico_id']}_{row['regiao_id']}"] = row['preco']

    matriz = []
    for s in servicos:
        item = {
            'id': s['id'],
            'nome': s['nome'],
            'categoria': s['categoria'],
            'unidade': s['unidade'],
            'preco_base': s['preco_base'],
            'precos_por_regiao': {}
        }
        for r in regioes:
            key = f"{s['id']}_{r['id']}"
            if key in precos_map:
                preco_val = precos_map[key]
            else:
                preco_val = round(s['preco_base'] * (r['multiplicador'] or 1.0), 2)
            item['precos_por_regiao'][r['id']] = preco_val
        matriz.append(item)

    conn.close()
    return jsonify({
        'regioes': regioes,
        'matriz': matriz
    })


@app.route('/api/atualizar-preco', methods=['POST'])
def api_atualizar_preco():
    dados = request.get_json() or {}
    servico_id = dados.get('servico_id')
    regiao_id = dados.get('regiao_id')
    preco = dados.get('preco')

    if servico_id is None or regiao_id is None or preco is None:
        return jsonify({'erro': 'Dados incompletos'}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO precos_regiao (servico_id, regiao_id, preco) 
        VALUES (?, ?, ?)
        ON CONFLICT(servico_id, regiao_id) DO UPDATE SET preco = excluded.preco
    ''', (servico_id, regiao_id, float(preco)))
    conn.commit()
    conn.close()
    return jsonify({'sucesso': True, 'mensagem': 'Preço salvo com sucesso!'})


# ======================== ROTAS DE ORÇAMENTOS ========================

def gerar_numero_orcamento():
    ano = datetime.now().year
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM orcamentos WHERE numero LIKE ?", (f"ORC-{ano}-%",))
    count = cur.fetchone()[0] + 1
    conn.close()
    return f"ORC-{ano}-{count:04d}"


@app.route('/api/orcamentos', methods=['GET', 'POST'])
def api_orcamentos():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        dados = request.get_json() or {}

        cliente_nome = dados.get('cliente_nome', '').strip()
        if not cliente_nome:
            conn.close()
            return jsonify({'erro': 'Nome do cliente é obrigatório'}), 400

        regiao_origem_id = dados.get('regiao_origem_id')
        regiao_origem_nome = dados.get('regiao_origem_nome', '')
        regiao_destino_id = dados.get('regiao_destino_id') or dados.get('regiao_id')
        regiao_destino_nome = dados.get('regiao_destino_nome') or dados.get('regiao_nome', '')

        regiao_id = regiao_destino_id
        regiao_nome = regiao_destino_nome

        if regiao_destino_id and not regiao_destino_nome:
            cur.execute('SELECT nome FROM regioes WHERE id = ?', (regiao_destino_id,))
            r_row = cur.fetchone()
            if r_row:
                regiao_destino_nome = r_row['nome']
                regiao_nome = r_row['nome']

        if regiao_origem_id and not regiao_origem_nome:
            cur.execute('SELECT nome FROM regioes WHERE id = ?', (regiao_origem_id,))
            ro_row = cur.fetchone()
            if ro_row:
                regiao_origem_nome = ro_row['nome']

        numero = dados.get('numero') or gerar_numero_orcamento()
        data_criacao = dados.get('data_criacao') or datetime.now().strftime('%d/%m/%Y')
        validade_dias = int(dados.get('validade_dias', 15) or 15)
        taxa_deslocamento = float(dados.get('taxa_deslocamento', 0.0) or 0.0)
        desconto = float(dados.get('desconto', 0.0) or 0.0)
        materiais_modo = dados.get('materiais_modo', 'cliente')
        forma_pagamento = dados.get('forma_pagamento', '')
        garantia = dados.get('garantia', '')
        prazo_execucao = dados.get('prazo_execucao', '')
        observacoes = dados.get('observacoes', '')
        status = dados.get('status', 'Pendente')

        itens = dados.get('itens', [])
        materiais = dados.get('materiais', [])

        total_servicos = sum(float(item.get('subtotal', 0.0)) for item in itens)
        total_materiais = sum(float(mat.get('subtotal', 0.0)) for mat in materiais) if materiais_modo == 'incluso' else 0.0

        total_geral = total_servicos + total_materiais + taxa_deslocamento - desconto

        cur.execute('''
            INSERT INTO orcamentos (
                numero, cliente_nome, cliente_telefone, cliente_email, cliente_endereco, cliente_cidade,
                regiao_origem_id, regiao_origem_nome, regiao_destino_id, regiao_destino_nome,
                regiao_id, regiao_nome, data_criacao, validade_dias, taxa_deslocamento, desconto,
                total_servicos, total_materiais, total_geral, materiais_modo, forma_pagamento,
                garantia, prazo_execucao, observacoes, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            numero, cliente_nome, dados.get('cliente_telefone', ''), dados.get('cliente_email', ''),
            dados.get('cliente_endereco', ''), dados.get('cliente_cidade', ''),
            regiao_origem_id, regiao_origem_nome, regiao_destino_id, regiao_destino_nome,
            regiao_id, regiao_nome, data_criacao, validade_dias, taxa_deslocamento, desconto,
            total_servicos, total_materiais, total_geral, materiais_modo, forma_pagamento,
            garantia, prazo_execucao, observacoes, status
        ))

        orcamento_id = cur.lastrowid

        # Salvar itens
        for it in itens:
            cur.execute('''
                INSERT INTO orcamento_itens (orcamento_id, servico_id, descricao, unidade, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                orcamento_id, it.get('servico_id'), it.get('descricao', ''), it.get('unidade', 'unidade'),
                float(it.get('quantidade', 1)), float(it.get('preco_unitario', 0)), float(it.get('subtotal', 0))
            ))

        # Salvar materiais
        for mat in materiais:
            cur.execute('''
                INSERT INTO orcamento_materiais (orcamento_id, descricao, unidade, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                orcamento_id, mat.get('descricao', ''), mat.get('unidade', 'un'),
                float(mat.get('quantidade', 1)), float(mat.get('preco_unitario', 0)), float(mat.get('subtotal', 0))
            ))

        conn.commit()
        conn.close()
        return jsonify({
            'sucesso': True,
            'id': orcamento_id,
            'numero': numero,
            'mensagem': 'Orçamento salvo com sucesso!'
        })

    # GET: Listar orçamentos
    cur.execute('SELECT * FROM orcamentos ORDER BY id DESC')
    orcamentos = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(orcamentos)


@app.route('/api/orcamentos/<int:orcamento_id>', methods=['GET', 'PUT', 'DELETE'])
def api_orcamento_detalhe(orcamento_id):
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'DELETE':
        cur.execute('DELETE FROM orcamentos WHERE id = ?', (orcamento_id,))
        conn.commit()
        conn.close()
        return jsonify({'sucesso': True, 'mensagem': 'Orçamento excluído com sucesso!'})

    if request.method == 'PUT':
        dados = request.get_json() or {}
        # Se for apenas atualização de status:
        if 'status' in dados and len(dados) == 1:
            cur.execute('UPDATE orcamentos SET status = ? WHERE id = ?', (dados['status'], orcamento_id))
            conn.commit()
            conn.close()
            return jsonify({'sucesso': True, 'mensagem': 'Status atualizado!'})

        # Edição completa do orçamento
        cliente_nome = dados.get('cliente_nome', '').strip()
        if not cliente_nome:
            conn.close()
            return jsonify({'erro': 'Nome do cliente é obrigatório'}), 400

        regiao_origem_id = dados.get('regiao_origem_id')
        regiao_origem_nome = dados.get('regiao_origem_nome', '')
        regiao_destino_id = dados.get('regiao_destino_id') or dados.get('regiao_id')
        regiao_destino_nome = dados.get('regiao_destino_nome') or dados.get('regiao_nome', '')

        validade_dias = int(dados.get('validade_dias', 15) or 15)
        taxa_deslocamento = float(dados.get('taxa_deslocamento', 0.0) or 0.0)
        desconto = float(dados.get('desconto', 0.0) or 0.0)
        materiais_modo = dados.get('materiais_modo', 'cliente')
        forma_pagamento = dados.get('forma_pagamento', '')
        garantia = dados.get('garantia', '')
        prazo_execucao = dados.get('prazo_execucao', '')
        observacoes = dados.get('observacoes', '')
        status = dados.get('status', 'Pendente')

        itens = dados.get('itens', [])
        materiais = dados.get('materiais', [])

        total_servicos = sum(float(item.get('subtotal', 0.0)) for item in itens)
        total_materiais = sum(float(mat.get('subtotal', 0.0)) for mat in materiais) if materiais_modo == 'incluso' else 0.0
        total_geral = total_servicos + total_materiais + taxa_deslocamento - desconto

        cur.execute('''
            UPDATE orcamentos SET
                cliente_nome = ?, cliente_telefone = ?, cliente_email = ?, cliente_endereco = ?, cliente_cidade = ?,
                regiao_origem_id = ?, regiao_origem_nome = ?, regiao_destino_id = ?, regiao_destino_nome = ?,
                regiao_id = ?, regiao_nome = ?, validade_dias = ?, taxa_deslocamento = ?, desconto = ?,
                total_servicos = ?, total_materiais = ?, total_geral = ?, materiais_modo = ?,
                forma_pagamento = ?, garantia = ?, prazo_execucao = ?, observacoes = ?, status = ?
            WHERE id = ?
        ''', (
            cliente_nome, dados.get('cliente_telefone', ''), dados.get('cliente_email', ''),
            dados.get('cliente_endereco', ''), dados.get('cliente_cidade', ''),
            regiao_origem_id, regiao_origem_nome, regiao_destino_id, regiao_destino_nome,
            regiao_destino_id, regiao_destino_nome, validade_dias, taxa_deslocamento, desconto,
            total_servicos, total_materiais, total_geral, materiais_modo, forma_pagamento,
            garantia, prazo_execucao, observacoes, status, orcamento_id
        ))

        # Atualiza itens
        cur.execute('DELETE FROM orcamento_itens WHERE orcamento_id = ?', (orcamento_id,))
        for it in itens:
            cur.execute('''
                INSERT INTO orcamento_itens (orcamento_id, servico_id, descricao, unidade, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                orcamento_id, it.get('servico_id'), it.get('descricao', ''), it.get('unidade', 'unidade'),
                float(it.get('quantidade', 1)), float(it.get('preco_unitario', 0)), float(it.get('subtotal', 0))
            ))

        # Atualiza materiais
        cur.execute('DELETE FROM orcamento_materiais WHERE orcamento_id = ?', (orcamento_id,))
        for mat in materiais:
            cur.execute('''
                INSERT INTO orcamento_materiais (orcamento_id, descricao, unidade, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                orcamento_id, mat.get('descricao', ''), mat.get('unidade', 'un'),
                float(mat.get('quantidade', 1)), float(mat.get('preco_unitario', 0)), float(mat.get('subtotal', 0))
            ))

        conn.commit()
        conn.close()
        return jsonify({
            'sucesso': True,
            'id': orcamento_id,
            'mensagem': 'Orçamento atualizado com sucesso!'
        })

    cur.execute('SELECT * FROM orcamentos WHERE id = ?', (orcamento_id,))
    orcamento = cur.fetchone()
    if not orcamento:
        conn.close()
        return jsonify({'erro': 'Orçamento não encontrado'}), 404

    cur.execute('SELECT * FROM orcamento_itens WHERE orcamento_id = ?', (orcamento_id,))
    itens = [dict(row) for row in cur.fetchall()]

    cur.execute('SELECT * FROM orcamento_materiais WHERE orcamento_id = ?', (orcamento_id,))
    materiais = [dict(row) for row in cur.fetchall()]

    conn.close()
    res = dict(orcamento)
    res['itens'] = itens
    res['materiais'] = materiais
    return jsonify(res)


@app.route('/api/orcamento/<int:orcamento_id>/texto-whatsapp')
def api_whatsapp_texto(orcamento_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM orcamentos WHERE id = ?', (orcamento_id,))
    orc = cur.fetchone()
    if not orc:
        conn.close()
        return jsonify({'erro': 'Não encontrado'}), 404

    cur.execute('SELECT * FROM orcamento_itens WHERE orcamento_id = ?', (orcamento_id,))
    itens = cur.fetchall()

    cur.execute('SELECT chave, valor FROM configuracoes')
    cfg = {row['chave']: row['valor'] for row in cur.fetchall()}
    conn.close()

    empresa = cfg.get('empresa_nome', 'Potencial Volt')
    resp = cfg.get('responsavel_nome', 'Fernando')
    tel = cfg.get('telefone', '')

    texto = f"⚡ *{empresa.upper()}* - Orçamento de Serviços Elétricos ⚡\n\n"
    texto += f"📋 *Orçamento:* {orc['numero']}\n"
    texto += f"👤 *Cliente:* {orc['cliente_nome']}\n"
    if orc['regiao_origem_nome']:
        texto += f"🏠 *Base / Onde Moro:* {orc['regiao_origem_nome']}\n"
    if orc['regiao_destino_nome']:
        texto += f"📍 *Local do Serviço:* {orc['regiao_destino_nome']}\n"
    elif orc['regiao_nome']:
        texto += f"📍 *Região de Atendimento:* {orc['regiao_nome']}\n"
    texto += f"📅 *Data:* {orc['data_criacao']} (Validade: {orc['validade_dias']} dias)\n\n"

    texto += "🔧 *SERVIÇOS SELECIONADOS:*\n"
    for i, it in enumerate(itens, 1):
        texto += f"{i}. {it['descricao']} ({it['quantidade']} {it['unidade']})\n"

    texto += f"\n💵 *Total dos Serviços:* R$ {orc['total_servicos']:.2f}\n"
    if orc['materiais_modo'] == 'incluso' and orc['total_materiais'] > 0:
        texto += f"📦 *Total de Materiais:* R$ {orc['total_materiais']:.2f}\n"
    elif orc['materiais_modo'] == 'cliente':
        texto += "⚠️ *Materiais:* Por conta do cliente / contratante.\n"
    if orc['desconto'] > 0:
        texto += f"🏷️ *Desconto Especial:* -R$ {orc['desconto']:.2f}\n"

    texto += f"💰 *VALOR TOTAL: R$ {orc['total_geral']:.2f}*\n\n"


    if orc['forma_pagamento']:
        texto += f"💳 *Condições de Pagamento:* {orc['forma_pagamento']}\n"
    if orc['garantia']:
        texto += f"🛡️ *Garantia:* {orc['garantia']}\n"
    if orc['prazo_execucao']:
        texto += f"⏱️ *Prazo de Execução:* {orc['prazo_execucao']}\n"

    texto += f"\nQualquer dúvida estou à disposição!\nAtenciosamente, *{resp}* ({empresa})\n📞 {tel}"

    return jsonify({'texto': texto})


if __name__ == '__main__':
    import webbrowser
    import threading

    def obter_ip_local():
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    ip_rede = obter_ip_local()

    def abrir_navegador():
        import time
        time.sleep(1.2)
        webbrowser.open('http://127.0.0.1:5000')

    threading.Thread(target=abrir_navegador, daemon=True).start()
    print("=" * 60)
    print("POTENCIAL VOLT - SISTEMA DE ORCAMENTOS POR REGIAO")
    print(f"Computador: http://127.0.0.1:5000")
    print(f"Acesso pelo Celular (mesmo Wi-Fi): http://{ip_rede}:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)

