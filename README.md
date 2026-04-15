# Sistema de RH

Sistema interno de Recursos Humanos para gestão de funcionários, folha de pagamento, ponto, férias, rescisão e relatórios.

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.14 + FastAPI |
| Banco de dados | SQLite (desenvolvimento) → PostgreSQL (produção) |
| ORM | SQLAlchemy 2.x |
| Autenticação | JWT + bcrypt + Refresh Token |
| Criptografia | Fernet (CPF, RG, conta bancária) |
| PDF | ReportLab |
| Frontend | HTML + CSS + JS |
| Desktop | PyWebView + PyInstaller |
| Deploy | Railway (backend) |

## Módulos

- **Funcionários** — cadastro completo, histórico de alterações, inativação
- **Costureiras** — lançamento mensal sem salário fixo
- **Folha de Pagamento** — cálculo automático com INSS, VT, horas extras, vales parcelados
- **Controle de Ponto** — 4 batidas/dia, banco de horas, tolerâncias
- **Férias** — gozo integral e fracionado, 1/3 constitucional, alerta de vencimento
- **13º Salário** — cálculo proporcional, lançamento automático em novembro/dezembro
- **Rescisão** — cálculo CLT completo, geração de PDF
- **Relatórios** — dashboard, custo por folha, aniversariantes, exportação CSV/PDF
- **Auditoria** — logs imutáveis de todas as ações relevantes

## Estrutura do projeto

```
rh-system/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # Rotas (controllers)
│   │   ├── core/               # Configurações e segurança
│   │   ├── db/                 # Conexão com banco de dados
│   │   ├── models/             # Models SQLAlchemy (tabelas)
│   │   ├── repositories/       # Acesso ao banco (queries)
│   │   ├── schemas/            # Schemas Pydantic (validação)
│   │   ├── services/           # Regras de negócio
│   │   └── utils/              # Utilitários gerais
│   ├── tests/                  # Testes automatizados
│   ├── create_tables.py        # Inicializa o banco de dados
│   └── requirements.txt
├── frontend/
│   ├── pages/                  # Telas HTML
│   ├── components/             # Componentes reutilizáveis
│   └── assets/                 # CSS, JS, imagens
├── .env.example                # Modelo de variáveis de ambiente
└── .gitignore
```

## Como rodar localmente

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/rh-system.git
cd rh-system
```

### 2. Criar e ativar o ambiente virtual

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

```bash
# Copie o arquivo de exemplo
cp ../.env.example .env
```

Edite o arquivo `.env` e gere as chaves de segurança:

```bash
# Gerar SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Gerar FERNET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 5. Criar as tabelas no banco

```bash
python create_tables.py
```

### 6. Iniciar o servidor

```bash
uvicorn app.main:app --reload
```

A API estará disponível em `http://localhost:8000`
Documentação automática em `http://localhost:8000/docs`

## Segurança

- Senhas armazenadas com **bcrypt** — nunca em texto puro
- Campos sensíveis (CPF, RG, conta bancária) criptografados com **Fernet**
- Autenticação via **JWT** com Access Token (30 min) + Refresh Token (7 dias)
- Todas as queries via **SQLAlchemy ORM** — sem SQL manual (proteção contra SQL Injection)
- **HTTPS** obrigatório em produção
- Logs de auditoria **imutáveis**

## Variáveis de ambiente

Veja o arquivo [.env.example](.env.example) para todas as variáveis necessárias.

> **Nunca suba o arquivo `.env` para o repositório.** Ele está no `.gitignore`.

## Deploy (produção)

O backend é implantado no **Railway** via `git push`. O Railway detecta automaticamente e faz o redeploy.

Para trocar para PostgreSQL, basta alterar `DATABASE_URL` no `.env`:

```
DATABASE_URL=postgresql://usuario:senha@host:5432/nome_do_banco
```
