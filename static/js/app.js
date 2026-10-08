// POTENCIAL VOLT - SISTEMA DE ORÇAMENTOS POR REGIÃO
// Lógica do Frontend com Cálculo de Deslocamento Origem ➔ Destino e Catálogo Interativo

let listaRegioes = [];
let regiaoOrigemAtual = null;
let regiaoDestinoAtual = null;
let servicosDaRegiao = [];
let itensOrcamento = [];
let materiaisOrcamento = [];
let configuracoesEmpresa = {};
let categoriaFiltroAtual = 'todas';
let ultimoOrcamentoId = null;

// ====================================================
// PWA & INSTALAÇÃO NO CELULAR
// ====================================================
let deferredPrompt = null;

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(reg => console.log('ServiceWorker registrado:', reg.scope))
            .catch(err => console.log('Erro ao registrar ServiceWorker:', err));
    });
}

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    const btn = document.getElementById('btnInstalarApp');
    if (btn) btn.classList.remove('d-none');
});

async function instalarAppPWA() {
    if (!deferredPrompt) {
        alert('Para instalar no seu celular:\n1. Toque nos 3 pontinhos do Chrome/Safari\n2. Escolha "Instalar aplicativo" ou "Adicionar à tela inicial"');
        return;
    }
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
        const btn = document.getElementById('btnInstalarApp');
        if (btn) btn.classList.add('d-none');
    }
    deferredPrompt = null;
}

// ====================================================
// INICIALIZAÇÃO
// ====================================================
document.addEventListener('DOMContentLoaded', () => {
    carregarConfiguracoesIniciais();
    carregarRegioes();
});

function formatarMoeda(valor) {
    return Number(valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

async function carregarConfiguracoesIniciais() {
    try {
        const res = await fetch('/api/configuracoes');
        configuracoesEmpresa = await res.json();
        if (configuracoesEmpresa.empresa_nome) {
            const el = document.getElementById('navEmpresaNome');
            if (el) el.innerHTML = `<i class="fa-solid fa-bolt-lightning text-warning me-1"></i> ${configuracoesEmpresa.empresa_nome}`;
        }
        if (configuracoesEmpresa.forma_pagamento_padrao) {
            document.getElementById('condPagamento').value = configuracoesEmpresa.forma_pagamento_padrao;
        }
        if (configuracoesEmpresa.garantia_padrao) {
            document.getElementById('condGarantia').value = configuracoesEmpresa.garantia_padrao;
        }
    } catch (err) {
        console.error('Erro ao carregar configurações:', err);
    }
}

// ====================================================
// GESTÃO DE ROTAS (ONDE MORO ➔ ONDE VOU FAZER O SERVIÇO)
// ====================================================
async function carregarRegioes() {
    try {
        const res = await fetch('/api/regioes');
        listaRegioes = await res.json();

        const selOrigem = document.getElementById('selectOrigem');
        const selDestino = document.getElementById('selectDestino');

        selOrigem.innerHTML = '';
        selDestino.innerHTML = '';

        if (listaRegioes.length === 0) {
            selOrigem.innerHTML = '<option value="">Nenhuma cidade cadastrada</option>';
            selDestino.innerHTML = '<option value="">Nenhuma cidade cadastrada</option>';
            return;
        }

        listaRegioes.forEach(r => {
            const optOrig = document.createElement('option');
            optOrig.value = r.id;
            optOrig.textContent = `🏠 ${r.nome}`;
            selOrigem.appendChild(optOrig);

            const optDest = document.createElement('option');
            optDest.value = r.id;
            optDest.textContent = `📍 ${r.nome}`;
            selDestino.appendChild(optDest);
        });

        // Define origem padrão (preferencialmente onde o usuário reside, ex: Belo Horizonte)
        const cidadePadrao = configuracoesEmpresa.cidade_origem_padrao || 'Belo Horizonte (BH)';
        const achouOrig = listaRegioes.find(r => r.nome.toLowerCase().includes('belo horizonte') || r.nome.toLowerCase().includes(cidadePadrao.toLowerCase()));
        if (achouOrig) {
            selOrigem.value = achouOrig.id;
        } else {
            selOrigem.value = listaRegioes[0].id;
        }

        // Define destino padrão
        selDestino.value = listaRegioes[0].id;

        aoMudarRota();

    } catch (err) {
        console.error('Erro ao carregar regiões:', err);
    }
}

async function aoMudarRota() {
    const origId = parseInt(document.getElementById('selectOrigem').value);
    const destId = parseInt(document.getElementById('selectDestino').value);

    if (!origId || !destId) return;

    regiaoOrigemAtual = listaRegioes.find(r => r.id === origId);
    regiaoDestinoAtual = listaRegioes.find(r => r.id === destId);

    // 1. Calcular Deslocamento Automático entre Origem e Destino
    try {
        const resDesloc = await fetch(`/api/calcular-deslocamento?origem_id=${origId}&destino_id=${destId}`);
        const dataDesloc = await resDesloc.json();
        const taxa = parseFloat(dataDesloc.valor_deslocamento || 0);

        // Atualizar interface do trajeto
        const txtTrajeto = `${dataDesloc.origem_nome} ➔ ${dataDesloc.destino_nome}`;
        document.getElementById('textoTrajeto').textContent = txtTrajeto;
        document.getElementById('badgeTaxaDeslocamento').textContent = formatarMoeda(taxa);
        document.getElementById('inputTaxaDeslocamento').value = taxa.toFixed(2);
        document.getElementById('resumoNomeRegiao').textContent = `${dataDesloc.destino_nome}`;
        document.getElementById('badgeCidadeDestino').textContent = dataDesloc.destino_nome;
        document.getElementById('subtituloCidadeServicos').textContent = dataDesloc.destino_nome;
        document.getElementById('clienteCidade').value = dataDesloc.destino_nome;

    } catch (err) {
        console.error('Erro ao calcular deslocamento:', err);
    }

    // 2. Carregar e Atualizar Preços dos Serviços para a Região de Destino
    try {
        const resPrecos = await fetch(`/api/precos/${destId}`);
        const dataPrecos = await resPrecos.json();

        servicosDaRegiao = dataPrecos.servicos;

        // SE JÁ EXISTEM ITENS NO ORÇAMENTO: atualizar automaticamente seus preços unitários para os preços da nova região de destino!
        if (itensOrcamento.length > 0) {
            itensOrcamento.forEach(item => {
                if (item.servico_id) {
                    const servEncontrado = servicosDaRegiao.find(s => s.servico_id === item.servico_id);
                    if (servEncontrado) {
                        item.preco_unitario = parseFloat(servEncontrado.preco_regiao);
                        item.subtotal = item.quantidade * item.preco_unitario;
                    }
                }
            });
            renderizarTabelaItensOrcamento();
        }

        // Renderizar a grade de cards com os novos preços atualizados
        renderizarGradeServicos();
        recalcularTotais();

    } catch (err) {
        console.error('Erro ao carregar preços da região de destino:', err);
    }
}

// ====================================================
// GRADE DE CARDS INTERATIVA DE SERVIÇOS
// ====================================================
function renderizarGradeServicos(filtroTexto = '') {
    const container = document.getElementById('gradeCardsServicos');
    container.innerHTML = '';

    let filtrados = servicosDaRegiao;

    // Filtro por categoria
    if (categoriaFiltroAtual && categoriaFiltroAtual !== 'todas') {
        filtrados = filtrados.filter(s => s.categoria.toLowerCase() === categoriaFiltroAtual.toLowerCase());
    }

    // Filtro por texto
    if (filtroTexto) {
        const f = filtroTexto.toLowerCase();
        filtrados = filtrados.filter(s => s.nome.toLowerCase().includes(f) || s.categoria.toLowerCase().includes(f) || (s.descricao && s.descricao.toLowerCase().includes(f)));
    }

    if (filtrados.length === 0) {
        container.innerHTML = `
            <div class="col-12 text-center py-4 text-muted">
                <i class="fa-solid fa-magnifying-glass fa-2x mb-2 text-black-50 d-block"></i>
                Nenhum serviço encontrado com esse filtro.
            </div>
        `;
        return;
    }

    filtrados.forEach(s => {
        // Verifica se já está selecionado
        const itemJaAdicionado = itensOrcamento.find(i => i.servico_id === s.servico_id);
        const qtdAtual = itemJaAdicionado ? itemJaAdicionado.quantidade : 1;
        const estaAdicionado = Boolean(itemJaAdicionado);

        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4';
        col.innerHTML = `
            <div class="service-card p-3 h-100 d-flex flex-column justify-content-between ${estaAdicionado ? 'item-adicionado' : ''}" id="card_serv_${s.servico_id}">
                <div>
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <span class="badge bg-light text-dark border small">${s.categoria}</span>
                        ${estaAdicionado ? '<span class="badge bg-success"><i class="fa-solid fa-check me-1"></i>Incluído (' + qtdAtual + ')</span>' : ''}
                    </div>
                    <h6 class="fw-bold text-navy mb-1">${s.nome}</h6>
                    <p class="text-muted small mb-2 text-truncate" title="${s.descricao || ''}">${s.descricao || 'Serviço técnico especializado'}</p>
                </div>
                
                <div class="border-top pt-2 mt-2">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="text-muted small">Preço na Região:</span>
                        <span class="service-price-tag text-primary">${formatarMoeda(s.preco_regiao)} <span class="fs-7 text-muted font-monospace">/${s.unidade}</span></span>
                    </div>

                    <div class="d-flex gap-2 align-items-center">
                        <div class="input-group input-group-sm" style="max-width: 90px;">
                            <input type="number" class="form-control text-center px-1" value="${qtdAtual}" min="1" step="1" id="qtd_input_${s.servico_id}">
                        </div>
                        <button type="button" class="btn btn-sm ${estaAdicionado ? 'btn-success' : 'btn-outline-primary'} flex-grow-1 fw-bold" onclick="adicionarServicoPeloCard(${s.servico_id})">
                            <i class="fa-solid ${estaAdicionado ? 'fa-plus' : 'fa-check'} me-1"></i> ${estaAdicionado ? 'Mais (+)' : 'Incluir'}
                        </button>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(col);
    });
}

function filtrarCatalogoServicos() {
    const texto = document.getElementById('buscaServicoRapido').value;
    renderizarGradeServicos(texto);
}

function filtrarPorCategoria(categoria, btnEl) {
    categoriaFiltroAtual = categoria;
    const botoes = document.querySelectorAll('#containerCategoriasFiltro .category-pill-btn');
    botoes.forEach(b => b.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');
    filtrarCatalogoServicos();
}

function adicionarServicoPeloCard(servicoId) {
    const serv = servicosDaRegiao.find(s => s.servico_id === servicoId);
    if (!serv) return;

    const inputQtd = document.getElementById(`qtd_input_${servicoId}`);
    const qtd = inputQtd ? (parseFloat(inputQtd.value) || 1) : 1;
    const valorUnit = parseFloat(serv.preco_regiao);

    const existente = itensOrcamento.find(i => i.servico_id === servicoId);
    if (existente) {
        existente.quantidade += qtd;
        existente.subtotal = existente.quantidade * existente.preco_unitario;
    } else {
        itensOrcamento.push({
            servico_id: serv.servico_id,
            descricao: serv.nome,
            unidade: serv.unidade,
            quantidade: qtd,
            preco_unitario: valorUnit,
            subtotal: qtd * valorUnit
        });
    }

    renderizarTabelaItensOrcamento();
    renderizarGradeServicos(document.getElementById('buscaServicoRapido').value);
    recalcularTotais();
}

// ====================================================
// ITENS DO ORÇAMENTO (TABELA E AJUSTES)
// ====================================================
function renderizarTabelaItensOrcamento() {
    const tbody = document.getElementById('corpoItensOrcamento');
    tbody.innerHTML = '';

    if (itensOrcamento.length === 0) {
        tbody.innerHTML = `
            <tr id="linhaSemItens">
                <td colspan="5" class="text-center py-4 text-muted">
                    <i class="fa-solid fa-cart-flatbed fa-2x mb-2 text-black-50 d-block"></i>
                    Nenhum serviço selecionado ainda. Clique em <strong>"+ Incluir"</strong> em qualquer serviço acima para adicioná-lo.
                </td>
            </tr>
        `;
        return;
    }

    itensOrcamento.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>
                <strong>${item.descricao}</strong>
                <span class="badge bg-light text-secondary border ms-2">${item.unidade}</span>
            </td>
            <td class="text-center" style="max-width: 110px;">
                <input type="number" class="form-control form-control-sm text-center" value="${item.quantidade}" min="1" step="0.5" onchange="alterarQtdItem(${index}, this.value)">
            </td>
            <td class="text-end" style="max-width: 130px;">
                <div class="input-group input-group-sm">
                    <span class="input-group-text">R$</span>
                    <input type="number" class="form-control text-end" value="${item.preco_unitario.toFixed(2)}" step="1" onchange="alterarPrecoItem(${index}, this.value)">
                </div>
            </td>
            <td class="text-end fw-bold text-navy">${formatarMoeda(item.subtotal)}</td>
            <td class="text-center">
                <button type="button" class="btn btn-outline-danger btn-sm" onclick="removerItem(${index})" title="Remover item">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function alterarQtdItem(index, novaQtd) {
    const q = parseFloat(novaQtd) || 1;
    itensOrcamento[index].quantidade = q;
    itensOrcamento[index].subtotal = q * itensOrcamento[index].preco_unitario;
    renderizarTabelaItensOrcamento();
    renderizarGradeServicos(document.getElementById('buscaServicoRapido').value);
    recalcularTotais();
}

function alterarPrecoItem(index, novoPreco) {
    const p = parseFloat(novoPreco) || 0;
    itensOrcamento[index].preco_unitario = p;
    itensOrcamento[index].subtotal = itensOrcamento[index].quantidade * p;
    renderizarTabelaItensOrcamento();
    recalcularTotais();
}

function removerItem(index) {
    itensOrcamento.splice(index, 1);
    renderizarTabelaItensOrcamento();
    renderizarGradeServicos(document.getElementById('buscaServicoRapido').value);
    recalcularTotais();
}

// ====================================================
// MATERIAIS
// ====================================================
function atualizarModoMateriais() {
    const modo = document.querySelector('input[name="materiaisModo"]:checked').value;
    const alerta = document.getElementById('alertaMateriaisCliente');
    const area = document.getElementById('areaAdicionarMateriais');
    const linhaResumo = document.getElementById('linhaResumoMateriais');

    if (modo === 'incluso') {
        alerta.style.display = 'none';
        area.style.display = 'block';
        linhaResumo.style.setProperty('display', 'flex', 'important');
    } else {
        alerta.style.display = 'flex';
        area.style.display = 'none';
        linhaResumo.style.setProperty('display', 'none', 'important');
    }
    recalcularTotais();
}

function adicionarMaterial() {
    const desc = document.getElementById('inputMatDescricao').value.trim();
    const unid = document.getElementById('inputMatUnidade').value.trim() || 'un';
    const qtd = parseFloat(document.getElementById('inputMatQtd').value) || 1;
    const preco = parseFloat(document.getElementById('inputMatPreco').value) || 0;

    if (!desc) {
        alert('Informe a descrição do material!');
        return;
    }

    materiaisOrcamento.push({
        descricao: desc,
        unidade: unid,
        quantidade: qtd,
        preco_unitario: preco,
        subtotal: qtd * preco
    });

    document.getElementById('inputMatDescricao').value = '';
    document.getElementById('inputMatQtd').value = 1;
    document.getElementById('inputMatPreco').value = '0.00';

    renderizarTabelaMateriais();
    recalcularTotais();
}

function renderizarTabelaMateriais() {
    const tbody = document.getElementById('corpoMateriais');
    tbody.innerHTML = '';

    if (materiaisOrcamento.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted small py-2">Nenhum material listado.</td></tr>';
        return;
    }

    materiaisOrcamento.forEach((m, idx) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${m.descricao}</td>
            <td class="text-center">${m.quantidade} ${m.unidade}</td>
            <td class="text-end">${formatarMoeda(m.preco_unitario)}</td>
            <td class="text-end fw-bold">${formatarMoeda(m.subtotal)}</td>
            <td class="text-center">
                <button type="button" class="btn btn-outline-danger btn-sm p-1" onclick="removerMaterial(${idx})">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function removerMaterial(idx) {
    materiaisOrcamento.splice(idx, 1);
    renderizarTabelaMateriais();
    recalcularTotais();
}

// ====================================================
// SUGESTÃO AUTOMÁTICA DE MATERIAIS COM PREÇOS DE MERCADO
// ====================================================
async function sugerirMateriais() {
    if (itensOrcamento.length === 0) {
        alert('Selecione pelo menos um serviço antes de sugerir materiais!');
        return;
    }

    const btn = document.getElementById('btnSugerirMateriais');
    const textoOriginal = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> Buscando...';
    btn.disabled = true;

    try {
        const servico_ids = itensOrcamento
            .filter(i => i.servico_id)
            .map(i => i.servico_id);

        const res = await fetch('/api/materiais-sugeridos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ servico_ids })
        });
        const data = await res.json();

        if (data.sucesso && data.materiais.length > 0) {
            // Adiciona apenas os que ainda não estão na lista
            let adicionados = 0;
            data.materiais.forEach(mat => {
                const jaExiste = materiaisOrcamento.some(m => m.descricao === mat.descricao);
                if (!jaExiste) {
                    materiaisOrcamento.push({
                        descricao: mat.descricao,
                        unidade: mat.unidade,
                        quantidade: mat.quantidade || 1,
                        preco_unitario: parseFloat(mat.preco),
                        subtotal: (mat.quantidade || 1) * parseFloat(mat.preco)
                    });
                    adicionados++;
                }
            });

            renderizarTabelaMateriais();
            recalcularTotais();

            if (adicionados > 0) {
                btn.innerHTML = `<i class="fa-solid fa-check me-1"></i> ${adicionados} materiais adicionados!`;
                btn.classList.replace('btn-info', 'btn-success');
            } else {
                btn.innerHTML = '<i class="fa-solid fa-check me-1"></i> Materiais ja listados';
                btn.classList.replace('btn-info', 'btn-secondary');
            }

            setTimeout(() => {
                btn.innerHTML = textoOriginal;
                btn.classList.remove('btn-success', 'btn-secondary');
                btn.classList.add('btn-info');
                btn.disabled = false;
            }, 3000);
        } else {
            btn.innerHTML = textoOriginal;
            btn.disabled = false;
            alert('Nenhum material especifico encontrado para os servicos selecionados.');
        }
    } catch (err) {
        console.error('Erro ao sugerir materiais:', err);
        btn.innerHTML = textoOriginal;
        btn.disabled = false;
        alert('Erro ao buscar sugestoes de materiais.');
    }
}


// ====================================================
// CÁLCULO DE TOTAIS
// ====================================================
function recalcularTotais() {
    const totalServicos = itensOrcamento.reduce((acc, it) => acc + (it.subtotal || 0), 0);

    const modoMat = document.querySelector('input[name="materiaisModo"]:checked').value;
    const totalMateriais = modoMat === 'incluso' ? materiaisOrcamento.reduce((acc, m) => acc + (m.subtotal || 0), 0) : 0;

    const taxaDeslocamento = parseFloat(document.getElementById('inputTaxaDeslocamento').value) || 0;
    const desconto = parseFloat(document.getElementById('inputDesconto').value) || 0;

    const totalGeral = totalServicos + totalMateriais + taxaDeslocamento - desconto;

    document.getElementById('resumoTotalServicos').textContent = formatarMoeda(totalServicos);
    document.getElementById('resumoTotalMateriais').textContent = formatarMoeda(totalMateriais);
    document.getElementById('resumoTotalGeral').textContent = formatarMoeda(totalGeral);

    return {
        totalServicos,
        totalMateriais,
        taxaDeslocamento,
        desconto,
        totalGeral
    };
}

// ====================================================
// GERAR ORÇAMENTO E ABRIR PDF IMEDIATO (PEDIDO DO USUÁRIO)
// ====================================================
async function gerarOrcamentoEImprimirPDF() {
    await salvarOrcamento(true);
}

async function salvarOrcamento(abrirPDFImediato = false) {
    const clienteNome = document.getElementById('clienteNome').value.trim();
    if (!clienteNome) {
        alert('Por favor, informe o nome do cliente!');
        document.getElementById('clienteNome').focus();
        return;
    }

    if (itensOrcamento.length === 0) {
        alert('Por favor, selecione pelo menos um serviço elétrico para gerar o orçamento!');
        return;
    }

    const origId = parseInt(document.getElementById('selectOrigem').value);
    const destId = parseInt(document.getElementById('selectDestino').value);

    const origNome = regiaoOrigemAtual ? regiaoOrigemAtual.nome : '';
    const destNome = regiaoDestinoAtual ? regiaoDestinoAtual.nome : '';

    const payload = {
        cliente_nome: clienteNome,
        cliente_telefone: document.getElementById('clienteTelefone').value.trim(),
        cliente_email: document.getElementById('clienteEmail').value.trim(),
        cliente_endereco: document.getElementById('clienteEndereco').value.trim(),
        cliente_cidade: destNome,
        regiao_origem_id: origId,
        regiao_origem_nome: origNome,
        regiao_destino_id: destId,
        regiao_destino_nome: destNome,
        regiao_id: destId,
        regiao_nome: destNome,
        taxa_deslocamento: parseFloat(document.getElementById('inputTaxaDeslocamento').value) || 0,
        desconto: parseFloat(document.getElementById('inputDesconto').value) || 0,
        materiais_modo: document.querySelector('input[name="materiaisModo"]:checked').value,
        forma_pagamento: document.getElementById('condPagamento').value.trim(),
        validade_dias: parseInt(document.getElementById('condValidade').value) || 15,
        prazo_execucao: document.getElementById('condPrazo').value.trim(),
        garantia: document.getElementById('condGarantia').value.trim(),
        observacoes: document.getElementById('condObservacoes').value.trim(),
        itens: itensOrcamento,
        materiais: materiaisOrcamento
    };

    const editandoId = document.getElementById('orcamentoEmEdicaoId').value;
    const url = editandoId ? `/api/orcamentos/${editandoId}` : '/api/orcamentos';
    const method = editandoId ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const resp = await res.json();

        if (resp.sucesso) {
            ultimoOrcamentoId = resp.id;

            // Se for para abrir PDF imediatamente:
            if (abrirPDFImediato) {
                // Abre tela de impressão com disparo automático do print
                window.open(`/orcamento/imprimir/${resp.id}?auto_print=1`, '_blank');
            }

            // Exibir modal de confirmação no app com resumo e botões rápidos
            document.getElementById('prontoOrcNumero').textContent = resp.numero || document.getElementById('numeroOrcamentoPreview').textContent;
            document.getElementById('prontoOrcCliente').textContent = clienteNome;
            document.getElementById('prontoOrcTrajeto').textContent = `${origNome} ➔ ${destNome}`;
            document.getElementById('prontoOrcTotal').textContent = document.getElementById('resumoTotalGeral').textContent;
            document.getElementById('btnProntoImprimirPDF').href = `/orcamento/imprimir/${resp.id}?auto_print=1`;

            const modalPronto = new bootstrap.Modal(document.getElementById('modalOrcamentoPronto'));
            modalPronto.show();

            limparFormularioOrcamento();
        } else {
            alert(`Erro ao salvar orçamento: ${resp.erro}`);
        }
    } catch (err) {
        console.error('Erro ao enviar orçamento:', err);
        alert('Erro ao conectar ao servidor local.');
    }
}

function limparFormularioOrcamento() {
    document.getElementById('orcamentoEmEdicaoId').value = '';
    const banner = document.getElementById('bannerModoEdicao');
    if (banner) banner.classList.add('d-none');
    document.getElementById('numeroOrcamentoPreview').textContent = 'ORC-AUTOMÁTICO';

    document.getElementById('clienteNome').value = '';
    document.getElementById('clienteTelefone').value = '';
    document.getElementById('clienteEmail').value = '';
    document.getElementById('clienteEndereco').value = '';
    document.getElementById('inputDesconto').value = '0.00';
    document.getElementById('condObservacoes').value = '';
    itensOrcamento = [];
    materiaisOrcamento = [];
    renderizarTabelaItensOrcamento();
    renderizarTabelaMateriais();
    renderizarGradeServicos();
    aoMudarRota();
}

// ====================================================
// HISTÓRICO DE ORÇAMENTOS
// ====================================================
async function carregarHistorico() {
    const tbody = document.getElementById('corpoHistorico');
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">Carregando histórico...</td></tr>';

    try {
        const res = await fetch('/api/orcamentos');
        const lista = await res.json();

        if (lista.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">Nenhum orçamento emitido ainda.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        lista.forEach(orc => {
            const tr = document.createElement('tr');
            tr.style.cursor = 'pointer';
            tr.title = 'Dê 2 cliques para abrir e imprimir este orçamento';
            tr.ondblclick = (e) => {
                // Não dispara se o clique duplo foi em select ou botão
                if (e.target.closest('select') || e.target.closest('button') || e.target.closest('a')) return;
                abrirOrcamentoImpressao(orc.id);
            };

            const trajetoInfo = (orc.regiao_origem_nome && orc.regiao_destino_nome) ? `${orc.regiao_origem_nome} ➔ ${orc.regiao_destino_nome}` : (orc.regiao_destino_nome || orc.regiao_nome || 'Geral');
            tr.innerHTML = `
                <td><strong>${orc.numero}</strong></td>
                <td>${orc.data_criacao}</td>
                <td>${orc.cliente_nome}</td>
                <td><span class="badge bg-primary-subtle text-primary border">${trajetoInfo}</span></td>
                <td class="text-end fw-bold">${formatarMoeda(orc.total_geral)}</td>
                <td class="text-center" onclick="event.stopPropagation()">
                    <select class="form-select form-select-sm d-inline-block w-auto" onchange="atualizarStatusOrcamento(${orc.id}, this.value)">
                        <option value="Pendente" ${orc.status === 'Pendente' ? 'selected' : ''}>⏳ Pendente</option>
                        <option value="Aprovado" ${orc.status === 'Aprovado' ? 'selected' : ''}>✅ Aprovado</option>
                        <option value="Concluído" ${orc.status === 'Concluído' ? 'selected' : ''}>🎉 Concluído</option>
                        <option value="Recusado" ${orc.status === 'Recusado' ? 'selected' : ''}>❌ Recusado</option>
                    </select>
                </td>
                <td class="text-center" onclick="event.stopPropagation()">
                    <div class="btn-group btn-group-sm">
                        <button type="button" class="btn btn-outline-warning text-dark" onclick="editarOrcamento(${orc.id})" title="Editar Orçamento">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button>
                        <button type="button" class="btn btn-outline-primary" onclick="abrirOrcamentoImpressao(${orc.id})" title="Abrir / Imprimir PDF">
                            <i class="fa-solid fa-print"></i>
                        </button>
                        <button type="button" class="btn btn-outline-success" onclick="abrirModalWhatsApp(${orc.id})" title="Enviar WhatsApp">
                            <i class="fa-brands fa-whatsapp"></i>
                        </button>
                        <button type="button" class="btn btn-outline-danger" onclick="excluirOrcamento(${orc.id})" title="Excluir">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Erro ao carregar histórico:', err);
    }
}

async function editarOrcamento(orcamentoId) {
    try {
        const res = await fetch(`/api/orcamentos/${orcamentoId}`);
        const orc = await res.json();
        if (!orc || orc.erro) {
            alert('Erro ao carregar dados do orçamento.');
            return;
        }

        // 1. Mudar para a Aba 1 (Novo Orçamento)
        const tabEl = document.querySelector('#novo-orcamento-tab');
        const tab = new bootstrap.Tab(tabEl);
        tab.show();

        // 2. Preencher ID de edição e banner
        document.getElementById('orcamentoEmEdicaoId').value = orc.id;
        document.getElementById('numeroOrcamentoPreview').textContent = orc.numero;
        const banner = document.getElementById('bannerModoEdicao');
        if (banner) banner.classList.remove('d-none');

        // 3. Preencher Dados do Cliente
        document.getElementById('clienteNome').value = orc.cliente_nome || '';
        document.getElementById('clienteTelefone').value = orc.cliente_telefone || '';
        document.getElementById('clienteEmail').value = orc.cliente_email || '';
        document.getElementById('clienteEndereco').value = orc.cliente_endereco || '';

        // 4. Selecionar Regiões de Origem e Destino
        if (orc.regiao_origem_id) {
            document.getElementById('selectOrigem').value = orc.regiao_origem_id;
        }
        if (orc.regiao_destino_id || orc.regiao_id) {
            document.getElementById('selectDestino').value = orc.regiao_destino_id || orc.regiao_id;
        }

        // 5. Preencher Condições e Totais
        document.getElementById('condPagamento').value = orc.forma_pagamento || '';
        document.getElementById('condValidade').value = orc.validade_dias || 15;
        document.getElementById('condPrazo').value = orc.prazo_execucao || '';
        document.getElementById('condGarantia').value = orc.garantia || '';
        document.getElementById('condObservacoes').value = orc.observacoes || '';
        document.getElementById('inputTaxaDeslocamento').value = (orc.taxa_deslocamento || 0).toFixed(2);
        document.getElementById('inputDesconto').value = (orc.desconto || 0).toFixed(2);

        // 6. Configurar Modo de Materiais
        if (orc.materiais_modo === 'incluso') {
            document.getElementById('modoMatIncluso').checked = true;
        } else {
            document.getElementById('modoMatCliente').checked = true;
        }
        atualizarModoMateriais();

        // 7. Carregar Itens e Materiais
        itensOrcamento = (orc.itens || []).map(i => ({
            servico_id: i.servico_id,
            descricao: i.descricao,
            unidade: i.unidade,
            quantidade: parseFloat(i.quantidade) || 1,
            preco_unitario: parseFloat(i.preco_unitario) || 0,
            subtotal: parseFloat(i.subtotal) || 0
        }));

        materiaisOrcamento = (orc.materiais || []).map(m => ({
            descricao: m.descricao,
            unidade: m.unidade,
            quantidade: parseFloat(m.quantidade) || 1,
            preco_unitario: parseFloat(m.preco_unitario) || 0,
            subtotal: parseFloat(m.subtotal) || 0
        }));

        // Atualizar views
        renderizarTabelaItensOrcamento();
        renderizarTabelaMateriais();
        recalcularTotais();

        // Rolar a tela suavemente para o topo do formulário
        window.scrollTo({ top: 0, behavior: 'smooth' });

    } catch (err) {
        console.error('Erro ao editar orçamento:', err);
        alert('Erro ao carregar o orçamento para edição.');
    }
}

function abrirOrcamentoImpressao(orcamentoId) {
    window.open(`/orcamento/imprimir/${orcamentoId}?auto_print=1`, '_blank');
}

function filtrarTabelaHistorico() {
    const texto = document.getElementById('filtroHistorico').value.toLowerCase();
    const linhas = document.querySelectorAll('#corpoHistorico tr');
    linhas.forEach(l => {
        l.style.display = l.textContent.toLowerCase().includes(texto) ? '' : 'none';
    });
}

async function atualizarStatusOrcamento(id, novoStatus) {
    try {
        await fetch(`/api/orcamentos/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: novoStatus })
        });
    } catch (err) {
        console.error('Erro ao atualizar status:', err);
    }
}

async function excluirOrcamento(id) {
    if (!confirm('Deseja realmente excluir este orçamento?')) return;
    try {
        await fetch(`/api/orcamentos/${id}`, { method: 'DELETE' });
        carregarHistorico();
    } catch (err) {
        console.error('Erro ao excluir:', err);
    }
}

// ====================================================
// MODAL WHATSAPP
// ====================================================
async function abrirModalWhatsApp(orcamentoId) {
    try {
        const res = await fetch(`/api/orcamento/${orcamentoId}/texto-whatsapp`);
        const data = await res.json();
        document.getElementById('textoWhatsApp').value = data.texto;
        const modal = new bootstrap.Modal(document.getElementById('modalWhatsApp'));
        modal.show();
    } catch (err) {
        console.error('Erro ao gerar mensagem de WhatsApp:', err);
    }
}

function copiarTextoWhatsApp() {
    const txt = document.getElementById('textoWhatsApp');
    txt.select();
    navigator.clipboard.writeText(txt.value).then(() => {
        alert('Texto copiado com sucesso! Agora é só colar no WhatsApp do cliente.');
    });
}

// ====================================================
// TABELA GERAL DE PREÇOS POR REGIÃO (MATRIZ)
// ====================================================
async function carregarMatrizPrecos() {
    const container = document.getElementById('containerMatrizPrecos');
    container.innerHTML = '<div class="text-center py-4 text-muted">Carregando matriz de preços...</div>';

    try {
        const res = await fetch('/api/matriz-precos');
        const data = await res.json();
        const regioes = data.regioes;
        const matriz = data.matriz;

        let html = `
            <table class="table table-bordered table-hover align-middle table-sm">
                <thead class="table-dark">
                    <tr>
                        <th style="min-width: 250px;">Serviço</th>
                        <th style="min-width: 140px;">Categoria</th>
                        <th class="text-center">Unid.</th>
                        <th class="text-end" style="min-width: 110px;">Preço Base</th>
        `;

        regioes.forEach(r => {
            html += `<th class="text-center bg-primary" style="min-width: 130px;">${r.nome}</th>`;
        });

        html += `
                    </tr>
                </thead>
                <tbody>
        `;

        matriz.forEach(item => {
            html += `
                <tr>
                    <td><strong>${item.nome}</strong></td>
                    <td><span class="badge bg-secondary-subtle text-dark border">${item.categoria}</span></td>
                    <td class="text-center text-muted small">${item.unidade}</td>
                    <td class="text-end text-muted">R$ ${item.preco_base.toFixed(2)}</td>
            `;

            regioes.forEach(r => {
                const precoVal = item.precos_por_regiao[r.id] || item.preco_base;
                html += `
                    <td class="text-center">
                        <div class="input-group input-group-sm">
                            <span class="input-group-text py-0 px-1">R$</span>
                            <input type="number" 
                                   class="form-control form-control-sm text-end fw-bold text-primary input-preco-matriz" 
                                   value="${parseFloat(precoVal).toFixed(2)}" 
                                   step="1"
                                   id="preco_${item.id}_${r.id}"
                                   onchange="salvarPrecoMatriz(${item.id}, ${r.id}, this)">
                        </div>
                    </td>
                `;
            });

            html += `</tr>`;
        });

        html += `
                </tbody>
            </table>
        `;

        container.innerHTML = html;

    } catch (err) {
        console.error('Erro ao carregar matriz de preços:', err);
    }
}

async function salvarPrecoMatriz(servicoId, regiaoId, inputEl) {
    const novoPreco = parseFloat(inputEl.value);
    if (isNaN(novoPreco) || novoPreco < 0) return;

    try {
        const res = await fetch('/api/atualizar-preco', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ servico_id: servicoId, regiao_id: regiaoId, preco: novoPreco })
        });
        const d = await res.json();
        if (d.sucesso) {
            inputEl.classList.add('is-valid');
            setTimeout(() => inputEl.classList.remove('is-valid'), 1500);
            // Se a região de destino atual for essa, atualiza na hora o catálogo!
            if (regiaoDestinoAtual && regiaoDestinoAtual.id === regiaoId) {
                const s = servicosDaRegiao.find(x => x.servico_id === servicoId);
                if (s) s.preco_regiao = novoPreco;
                renderizarGradeServicos();
            }
        }
    } catch (err) {
        console.error('Erro ao salvar preço:', err);
        inputEl.classList.add('is-invalid');
    }
}

// ====================================================
// GESTÃO DE SERVIÇOS & REGIÕES (CADASTROS)
// ====================================================
async function carregarCadastros() {
    carregarListaRegioesCadastradas();
    carregarListaServicosCadastrados();
}

async function carregarListaRegioesCadastradas() {
    const listGroup = document.getElementById('listaRegioesCadastradas');
    try {
        const res = await fetch('/api/regioes');
        const regioes = await res.json();

        listGroup.innerHTML = '';
        regioes.forEach(r => {
            const item = document.createElement('div');
            item.className = 'list-group-item d-flex justify-content-between align-items-center';
            item.innerHTML = `
                <div>
                    <h6 class="mb-1 fw-bold text-navy"><i class="fa-solid fa-map-pin text-primary me-2"></i>${r.nome}</h6>
                    <small class="text-muted d-block">${r.descricao || 'Sem descrição'}</small>
                    <span class="badge bg-light text-dark border me-1">Taxa padrão: ${formatarMoeda(r.taxa_deslocamento)}</span>
                    <span class="badge bg-light text-dark border">Mult: ${r.multiplicador}x</span>
                </div>
                <div>
                    <button class="btn btn-outline-danger btn-sm" onclick="excluirRegiao(${r.id})" title="Desativar Cidade">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            `;
            listGroup.appendChild(item);
        });
    } catch (err) {
        console.error('Erro ao carregar regiões:', err);
    }
}

async function carregarListaServicosCadastrados() {
    const tbody = document.getElementById('corpoServicosCadastrados');
    try {
        const res = await fetch('/api/servicos');
        const servicos = await res.json();

        tbody.innerHTML = '';
        servicos.forEach(s => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${s.nome}</strong></td>
                <td><span class="badge bg-light text-secondary border">${s.categoria}</span></td>
                <td>${s.unidade}</td>
                <td class="text-end fw-bold text-navy">${formatarMoeda(s.preco_base)}</td>
                <td class="text-center">
                    <button class="btn btn-outline-danger btn-sm" onclick="excluirServico(${s.id})" title="Desativar Serviço">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Erro ao carregar serviços:', err);
    }
}

function abrirModalNovaRegiao() {
    document.getElementById('modalRegiaoId').value = '';
    document.getElementById('modalRegiaoNome').value = '';
    document.getElementById('modalRegiaoDescricao').value = '';
    document.getElementById('modalRegiaoTaxa').value = '0.00';
    document.getElementById('modalRegiaoMult').value = '1.0';
    new bootstrap.Modal(document.getElementById('modalRegiao')).show();
}

async function salvarModalRegiao() {
    const nome = document.getElementById('modalRegiaoNome').value.trim();
    if (!nome) {
        alert('Informe o nome da cidade / região!');
        return;
    }

    const payload = {
        nome: nome,
        descricao: document.getElementById('modalRegiaoDescricao').value.trim(),
        taxa_deslocamento: parseFloat(document.getElementById('modalRegiaoTaxa').value) || 0,
        multiplicador: parseFloat(document.getElementById('modalRegiaoMult').value) || 1.0
    };

    try {
        const res = await fetch('/api/regioes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.sucesso) {
            bootstrap.Modal.getInstance(document.getElementById('modalRegiao')).hide();
            carregarRegioes();
            carregarListaRegioesCadastradas();
        } else {
            alert(data.erro);
        }
    } catch (err) {
        console.error('Erro ao salvar região:', err);
    }
}

async function excluirRegiao(id) {
    if (!confirm('Deseja desativar esta cidade / região?')) return;
    await fetch(`/api/regioes/${id}`, { method: 'DELETE' });
    carregarRegioes();
    carregarListaRegioesCadastradas();
}

function abrirModalNovoServico() {
    document.getElementById('modalServicoId').value = '';
    document.getElementById('modalServicoNome').value = '';
    document.getElementById('modalServicoDescricao').value = '';
    document.getElementById('modalServicoPrecoBase').value = '';
    new bootstrap.Modal(document.getElementById('modalServico')).show();
}

async function salvarModalServico() {
    const nome = document.getElementById('modalServicoNome').value.trim();
    const preco = parseFloat(document.getElementById('modalServicoPrecoBase').value);

    if (!nome || isNaN(preco)) {
        alert('Preencha o nome do serviço e o preço base!');
        return;
    }

    const payload = {
        nome: nome,
        categoria: document.getElementById('modalServicoCategoria').value,
        unidade: document.getElementById('modalServicoUnidade').value.trim() || 'unidade',
        preco_base: preco,
        descricao: document.getElementById('modalServicoDescricao').value.trim()
    };

    try {
        const res = await fetch('/api/servicos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.sucesso) {
            bootstrap.Modal.getInstance(document.getElementById('modalServico')).hide();
            carregarListaServicosCadastrados();
            aoMudarRota();
        } else {
            alert(data.erro);
        }
    } catch (err) {
        console.error('Erro ao salvar serviço:', err);
    }
}

async function excluirServico(id) {
    if (!confirm('Deseja desativar este serviço?')) return;
    await fetch(`/api/servicos/${id}`, { method: 'DELETE' });
    carregarListaServicosCadastrados();
    aoMudarRota();
}

// ====================================================
// CONFIGURAÇÕES DA EMPRESA
// ====================================================
async function carregarConfiguracoes() {
    try {
        const res = await fetch('/api/configuracoes');
        const cfg = await res.json();
        document.getElementById('cfgEmpresaNome').value = cfg.empresa_nome || '';
        document.getElementById('cfgEmpresaSlogan').value = cfg.empresa_slogan || '';
        document.getElementById('cfgResponsavelNome').value = cfg.responsavel_nome || '';
        document.getElementById('cfgTelefone').value = cfg.telefone || '';
        document.getElementById('cfgEmail').value = cfg.email || '';
        document.getElementById('cfgChavePix').value = cfg.chave_pix || '';
        document.getElementById('cfgCidadeSede').value = cfg.cidade_sede || '';
        document.getElementById('cfgGarantiaPadrao').value = cfg.garantia_padrao || '';
        document.getElementById('cfgFormaPagamentoPadrao').value = cfg.forma_pagamento_padrao || '';
    } catch (err) {
        console.error('Erro ao carregar configurações:', err);
    }
}

async function salvarConfiguracoes(e) {
    e.preventDefault();
    const payload = {
        empresa_nome: document.getElementById('cfgEmpresaNome').value.trim(),
        empresa_slogan: document.getElementById('cfgEmpresaSlogan').value.trim(),
        responsavel_nome: document.getElementById('cfgResponsavelNome').value.trim(),
        telefone: document.getElementById('cfgTelefone').value.trim(),
        email: document.getElementById('cfgEmail').value.trim(),
        chave_pix: document.getElementById('cfgChavePix').value.trim(),
        cidade_sede: document.getElementById('cfgCidadeSede').value.trim(),
        garantia_padrao: document.getElementById('cfgGarantiaPadrao').value.trim(),
        forma_pagamento_padrao: document.getElementById('cfgFormaPagamentoPadrao').value.trim()
    };

    try {
        const res = await fetch('/api/configuracoes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.sucesso) {
            alert('Configurações da empresa salvas com sucesso!');
            carregarConfiguracoesIniciais();
        }
    } catch (err) {
        console.error('Erro ao salvar configurações:', err);
    }
}
