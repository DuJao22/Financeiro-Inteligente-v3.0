# Instalação Local - Sistema Financeiro SQLite3

## Para Python 3.13

### 1. Instalar dependências compatíveis:

```bash
pip install -r requirements_python313.txt
```

### 2. Executar o sistema:

```bash
python main.py
```

### 3. Acessar o sistema:
- URL: http://localhost:5000
- O banco SQLite3 será criado automaticamente como `financial_system.db`

## Versões testadas e compatíveis:

- **Python:** 3.13
- **Flask:** 2.3.3 (compatível com MarkupSafe)
- **Flask-WTF:** 1.1.1 (sem problemas de Markup)
- **SQLite3:** Incluído no Python (sem dependências externas)

## Estrutura do banco:
- **users** - Usuários e autenticação
- **transactions** - Transações financeiras  
- **accounts** - Contas a pagar/receber
- **financial_goals** - Metas financeiras

## Funcionalidades:
✅ Sistema de login/registro
✅ Dashboard com gráficos
✅ Controle de caixa
✅ Contas a pagar/receber
✅ Relatórios PDF
✅ Sistema de assinaturas

## Em caso de erro:
1. Verifique a versão do Python: `python --version`
2. Use o ambiente virtual: `python -m venv venv && venv\Scripts\activate`
3. Instale as dependências: `pip install -r requirements_python313.txt`