# ⚡ Potencial Volt - Sistema de Orçamentos Elétricos por Região

Sistema completo e profissional desenvolvido sob medida para a **Potencial Volt** para geração de orçamentos de serviços elétricos com precificação inteligente e automática por região de atendimento.

---

## 🚀 Como Iniciar o Programa

Você pode iniciar o programa de **duas formas muito simples**:

### Opção 1: Com 1 Clique (Recomendado)
- Dê um duplo clique no arquivo:
  `iniciar_programa.bat`
- O servidor iniciará e o seu navegador abrirá automaticamente na tela do sistema (`http://127.0.0.1:5000`).

### Opção 2: Pelo Terminal / Prompt de Comando
```bash
python app.py
```

---

## 🎯 Como Funciona o Novo Fluxo de Orçamento

1. **Passo 1 — Selecione o Trajeto (Origem ➔ Destino):**
   - **🏠 Onde Eu Moro (Sua Base / Saída):** Escolha sua cidade base (ex: *Belo Horizonte (BH)*, *Vespasiano*, etc.).
   - **📍 Onde Vou Fazer o Serviço (Local do Cliente):** Escolha onde o cliente está (ex: *Lagoa Santa*, *Pedro Leopoldo*, *São José da Lapa*, etc.).
   - **🚗 Cálculo Automático do Deslocamento:** O programa calcula na hora a taxa de deslocamento entre as duas cidades (ex: BH ➔ Lagoa Santa = R$ 45,00) e já carrega **os preços atualizados dos serviços elétricos daquela cidade de destino**!
2. **Passo 2 — Dados do Cliente:**
   - Preencha o nome do cliente, telefone/WhatsApp e endereço.
3. **Passo 3 — Formulário de Seleção de Serviços Elétricos:**
   - Navegue pelos serviços em cartões visuais (organizados por categorias: *Quadro de Distribuição*, *Chuveiros*, *Tomadas & Interruptores*, *Iluminação*, *Instalação Completa*, etc.).
   - Os valores de cada serviço já aparecem na tela **com o preço cobrado na cidade do serviço**.
   - Basta clicar em **"+ Incluir"** ou ajustar a quantidade para adicionar diretamente ao orçamento.
4. **Passo 4 — Gerar Orçamento com PDF Imediato:**
   - Clique no botão de destaque: **⚡ GERAR ORÇAMENTO & ABRIR PDF**.
   - O orçamento é salvo com o **VALOR TOTAL** calculado (serviços + deslocamento da rota).
   - A folha de proposta em formato **A4 profissional abre na hora com a janela de impressão pronta para salvar em PDF** (`Ctrl+P` / Salvar em PDF).
   - Também abre na tela a opção de **Copiar Mensagem Pronta para o WhatsApp** com 1 clique!


---

## 🛠️ Principais Recursos do Sistema

- **📍 Gestão de Regiões:**
  - Cadastre quantas regiões/bairros/cidades desejar com taxa de deslocamento e multiplicador base.
- **⚡ Catálogo Completo de Serviços Elétricos:**
  - Já vem pré-cadastrado com mais de 20 serviços elétricos da sua planilha original (troca de disjuntores, chuveiros, QDC, cabeamento, iluminação, tomadas, infraestrutura, reformas completas, etc.).
- **📊 Tabela Geral de Preços (Matriz de Regiões):**
  - Visualize uma tabela completa com todos os serviços em linhas e as regiões em colunas.
  - Altere o preço de qualquer serviço em qualquer região diretamente na tela e o sistema salva na hora.
- **📦 Gestão de Materiais (Opcional):**
  - Escolha com 1 clique se os materiais são **por conta do cliente** ou **inclusos no orçamento** (com lista de peças e quantidades).
- **🖨️ Emissão e Impressão Profissional (Formato A4 / PDF):**
  - Layout pronto para impressão ou salvar em PDF no padrão comercial da Potencial Volt, com dados do cliente, especificação técnica, tabela discriminada, garantias (NBR-5410) e campo para assinaturas.
- **📱 Envio Rápido para WhatsApp:**
  - Botão que gera o texto formatado completo do orçamento com emojis e valores pronto para colar no WhatsApp do cliente com 1 clique.
- **📂 Histórico de Orçamentos:**
  - Registre propostas com status (*Pendente*, *Aprovado*, *Concluído*, *Recusado*), reimprima ou consulte a qualquer momento.
- **🏢 Dados da Empresa Personalizáveis:**
  - Altere nome, responsável técnico, telefone, e-mail, chave PIX e termos de garantia na aba de configurações.

---

## 📁 Estrutura dos Arquivos

- [iniciar_programa.bat](file:///c:/Users/fernando.carmo/Desktop/Fernando/Potencial%20Volt/iniciar_programa.bat) - Inicializador de 1 clique no Windows
- [app.py](file:///c:/Users/fernando.carmo/Desktop/Fernando/Potencial%20Volt/app.py) - Servidor backend da aplicação
- [database.py](file:///c:/Users/fernando.carmo/Desktop/Fernando/Potencial%20Volt/database.py) - Banco de dados SQLite (`orcamentos_eletrica.db`)
- [templates/index.html](file:///c:/Users/fernando.carmo/Desktop/Fernando/Potencial%20Volt/templates/index.html) - Interface principal do sistema
- [templates/orcamento_print.html](file:///c:/Users/fernando.carmo/Desktop/Fernando/Potencial%20Volt/templates/orcamento_print.html) - Modelo de impressão/PDF da proposta comercial
- [static/css/style.css](file:///c:/Users/fernando.carmo/Desktop/Fernando/Potencial%20Volt/static/css/style.css) - Estilo visual da Potencial Volt
- [static/js/app.js](file:///c:/Users/fernando.carmo/Desktop/Fernando/Potencial%20Volt/static/js/app.js) - Lógica interativa de cálculo e atualização em tempo real
