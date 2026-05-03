# Roteiro de Produção — Sistema de RH

**Autor:** Lucas Mello
**Data:** 30/04/2026
**Status:** Em andamento

---

## Visão Geral

Sistema de RH web (FastAPI + SQLite → PostgreSQL + JavaScript Vanilla) desenvolvido para uso de uma empresa cliente com cobrança mensal de licença. O objetivo deste roteiro é guiar todas as etapas necessárias para levar o sistema a um ambiente de produção seguro, estável e sustentável.

---

## Stack Definida para Produção

| Camada            | Tecnologia         | Observação                            |
| ----------------- | ------------------ | --------------------------------------- |
| Backend           | FastAPI (Python)   | Já implementado                        |
| Frontend          | JavaScript Vanilla | Já implementado                        |
| Banco de dados    | PostgreSQL         | Migrar do SQLite atual via Supabase     |
| Hospedagem        | Railway            | Deploy automático via GitHub           |
| Email             | Resend             | Notificações e recuperação de senha |
| Containerização | Docker             | Dockerfile único (backend + frontend)  |

---

## Fase 1 — Segurança ⚠️ (PRIORIDADE MÁXIMA)

> Executar obrigatoriamente antes de qualquer deploy em produção.

### 1.1 Auditoria de Vulnerabilidades

- [x] **SQL Injection** — confirmado: todas as queries usam SQLAlchemy ORM, sem raw SQL inseguro
- [x] **Autenticação JWT** — migrado de python-jose (CVEs) para PyJWT 2.10.1; HS256, 30min access / 7 dias refresh, `jti` único por token
- [x] **CORS aberto** — corrigido: agora usa `settings.allowed_origins_list` do `.env` em vez de `["*"]`
- [x] **Rate limiting** — implementado com slowapi: 5/min no login, 3/min no forgot-password, 5/min no reset-password
- [x] **Variáveis sensíveis** — confirmado: `SECRET_KEY` e `FERNET_KEY` são obrigatórios via `.env`, validados na inicialização, nunca hardcoded
- [x] **Endpoints sem autenticação** — corrigido: auditoria completa de 117 rotas; `POST /api/v1/company` sem auth corrigido com `require_admin`
- [x] **Isolamento por empresa** — confirmado: `company_id` validado nos serviços críticos (payroll, vacation, termination, employee)
- [ ] **HTTPS obrigatório** — pendente: HSTS header adicionado, mas redirect HTTP→HTTPS depende do deploy (Railway)
- [x] **Logs de erro** — confirmado: FastAPI não expõe stack trace por padrão; `/health` simplificado (versão removida); `/openapi.json` desabilitado em produção
- [ ] **Dependências desatualizadas** — pendente: pip-audit não instalado no ambiente, rodar após setup de produção
- [x] **Criptografia de CPF** — confirmado: Fernet aplicado em CPF, RG e conta bancária em todos os fluxos de criação e leitura
- [x] **Exposição de docs** — confirmado e reforçado: `/docs`, `/redoc` e `/openapi.json` desabilitados quando `ENVIRONMENT != development`

### 1.2 Correções Prioritárias Identificadas

| Item                      | Risco    | Status | Ação                               |
| ------------------------- | -------- | ------ | ------------------------------------ |
| `allow_origins=["*"]`   | Alto     | ✅ Feito | Usando `settings.allowed_origins_list` |
| Sem rate limit no login   | Alto     | ✅ Feito | slowapi 5/min implementado          |
| SECRET_KEY no código     | Crítico  | ✅ Feito | Confirmado via `.env` obrigatório   |
| Stack trace em produção  | Médio   | ✅ Feito | FastAPI padrão + `/health` limpo    |
| Docs públicos            | Baixo    | ✅ Feito | `/docs`, `/redoc` e `/openapi.json` desabilitados |
| Senha fraca (4 chars)    | Alto     | ✅ Feito | Mínimo 9 chars + maiúscula + minúscula + número + especial |
| Headers de segurança ausentes | Médio | ✅ Feito | X-Frame-Options, X-XSS-Protection, HSTS, Referrer-Policy |
| python-jose com CVEs     | Médio    | ✅ Feito | Migrado para PyJWT 2.10.1 |

---

## Fase 2 — Banco de Dados

> Migrar de SQLite para PostgreSQL antes do deploy.

- [ ] Criar projeto no **Supabase** e obter connection string PostgreSQL
- [ ] Atualizar `DATABASE_URL` no `.env` para apontar para o Supabase
- [ ] Ajustar tipos incompatíveis entre SQLite e PostgreSQL (Boolean, JSON, etc.)
- [ ] Substituir os `ALTER TABLE` manuais em `_run_migrations()` por **Alembic** (migrations versionadas)
- [ ] Testar todos os endpoints após a migração (folha, férias, rescisão, costureiras, ponto)
- [ ] Verificar que `Base.metadata.create_all()` cria as tabelas corretamente no PostgreSQL
- [ ] Configurar **backup automático diário** no Supabase (já disponível no painel)
- [ ] Garantir que `DATABASE_URL` nunca está hardcoded — sempre via variável de ambiente

---

## Fase 3 — Sistema de Licença

> Garantir receita recorrente e bloqueio automático em caso de inadimplência.

### Modelo de Negócio

- Cliente paga mensalmente via PIX
- Você renova a licença manualmente após confirmação do pagamento
- Se não renovar, o sistema bloqueia automaticamente na data de vencimento
- Carência de X dias configurável antes do bloqueio total

### Implementação Técnica

**Tabela no banco:**

```sql
licenses (
  id           SERIAL PRIMARY KEY,
  company_id   INTEGER REFERENCES companies(id),
  valid_until  DATE NOT NULL,
  is_active    BOOLEAN DEFAULT TRUE,
  created_at   TIMESTAMP DEFAULT NOW(),
  updated_at   TIMESTAMP DEFAULT NOW()
)
```

**Middleware FastAPI:**

- A cada request autenticado, verifica se `valid_until >= hoje` e `is_active = true`
- Se vencida → retorna `402 Payment Required`
- Frontend detecta 402 → exibe tela de bloqueio com seus dados de contato

**Endpoint de renovação (protegido por senha master):**

```
POST /admin/license/renew
{ "company_id": 1, "months": 1 }
```

- [ ] Criar tabela `licenses` no banco
- [ ] Implementar middleware de verificação de licença
- [ ] Criar endpoint de renovação protegido
- [ ] Implementar tela de bloqueio no frontend com dados de contato
- [ ] Configurar carência (ex: 3 dias após vencimento antes de bloquear)
- [ ] Testar fluxo completo: vencimento → bloqueio → renovação → desbloqueio

### Tela de Bloqueio (exemplo)

```
⚠ Acesso Suspenso

Sua licença venceu em DD/MM/AAAA.
Entre em contato para renovar o acesso.

📱 (xx) xxxxx-xxxx
📧 seu@email.com
```

---

## Fase 4 — Deploy

### 4.1 Docker

- [ ] Criar `Dockerfile` na raiz do projeto
  - Imagem Python para o backend FastAPI
  - Servir frontend estático pelo próprio FastAPI ou Nginx
- [ ] Testar build local: `docker build` e `docker run`
- [ ] Criar `.dockerignore` para excluir arquivos desnecessários

**Estrutura sugerida do Dockerfile:**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ ./backend/
COPY frontend/ ./frontend/
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4.2 Variáveis de Ambiente

- [ ] Criar arquivo `.env.example` com todas as variáveis necessárias (sem valores reais)
- [ ] Confirmar que `.env` está no `.gitignore`
- [ ] Configurar variáveis no painel da Railway:
  - `DATABASE_URL`
  - `SECRET_KEY`
  - `ENVIRONMENT=production`
  - `APP_VERSION`

### 4.3 Railway

- [ ] Criar conta na Railway e conectar ao repositório GitHub
- [ ] Configurar deploy automático no push para a branch `main`
- [ ] Configurar domínio personalizado
- [ ] Verificar SSL automático (HTTPS)
- [ ] Testar ambiente de produção completo após primeiro deploy

### 4.4 Checklist pré-go-live

- [ ] Todos os endpoints respondendo corretamente
- [ ] Login e autenticação funcionando
- [ ] Folha de pagamento calculando corretamente
- [ ] Férias, rescisão e 13º funcionando
- [ ] Sistema de licença ativo e testado
- [ ] HTTPS ativo
- [ ] Logs sem dados sensíveis expostos

---

## Fase 5 — Qualidade e Funcionalidades Futuras

> Implementar após o cliente já estar usando o sistema em produção.

### Email (Resend)

- [ ] Integrar Resend ao FastAPI (`pip install resend`)
- [ ] Email de boas-vindas ao cadastrar novo usuário
- [ ] Recuperação de senha por email com token temporário
- [ ] Notificação automática quando férias de funcionário estiver vencendo
- [ ] Relatório mensal resumido enviado por email para o RH

### Testes Automatizados

- [ ] Testes nos endpoints críticos: login, folha, férias, rescisão
- [ ] Rodar testes automaticamente no GitHub Actions antes do deploy

### Monitoramento

- [ ] Configurar alertas de erro (ex: Sentry — free tier disponível)
- [ ] Dashboard de uptime (ex: UptimeRobot — gratuito)

### Pagamento Automatizado (futuro, se escalar para mais clientes)

- [ ] Integrar Stripe ou Pagar.me para cobrar automaticamente
- [ ] Webhook de pagamento confirmado → renova licença automaticamente
- [ ] Webhook de falha de pagamento → envia aviso por email antes de bloquear

---

## Ordem de Execução Recomendada

```
1. Segurança (Fase 1)
        ↓
2. Migração PostgreSQL (Fase 2)
        ↓
3. Sistema de Licença (Fase 3)
        ↓
4. Docker + Deploy Railway (Fase 4)
        ↓
5. Email, Testes e Monitoramento (Fase 5)
```

> Não pular etapas. Segurança e banco de dados são pré-requisitos para tudo.

---

## Estimativa de Custos Mensais (produção)

| Serviço        | Plano       | Custo estimado            |
| --------------- | ----------- | ------------------------- |
| Railway         | Hobby       | ~$5–10/mês              |
| Supabase        | Free tier   | Grátis (até 500MB)      |
| Resend          | Free tier   | Grátis (3k emails)       |
| Domínio        | Registro.br | ~R$ 40/ano                |
| **Total** |             | **~R$ 50–80/mês** |

---

## Contato e Repositório

- **Repositório:** github.com/DevLucasMelloo/rh-system
- **Branch principal:** `main`
- **Deploy automático:** a cada push na `main`
