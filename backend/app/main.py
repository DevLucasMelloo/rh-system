from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.database import Base, engine
import app.models  # noqa: F401 — garante que todos os modelos sejam registrados

# ── Rate limiter global ────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


def _run_sqlite_migrations():
    """Aplica colunas novas em tabelas existentes — apenas para SQLite (sem ADD COLUMN IF NOT EXISTS)."""
    from sqlalchemy import text
    migrations = [
        "ALTER TABLE vacations ADD COLUMN sell_all_days BOOLEAN DEFAULT 0",
        "ALTER TABLE vacations ADD COLUMN abono_days INTEGER DEFAULT 0",
        "ALTER TABLE timesheet_entries ADD COLUMN is_recess BOOLEAN DEFAULT 0",
        "ALTER TABLE timesheet_entries ADD COLUMN is_compensar BOOLEAN DEFAULT 0",
        "ALTER TABLE timesheet_entries ADD COLUMN is_dsr_deducted BOOLEAN DEFAULT 0",
        "ALTER TABLE terminations ADD COLUMN notice_start_date DATE",
        "ALTER TABLE terminations ADD COLUMN status VARCHAR(20) DEFAULT 'pendente'",
        "ALTER TABLE terminations ADD COLUMN saldo_dias INTEGER DEFAULT 0",
        "ALTER TABLE terminations ADD COLUMN ferias_meses_prop INTEGER DEFAULT 0",
        "ALTER TABLE terminations ADD COLUMN ferias_meses_venc INTEGER DEFAULT 0",
        "ALTER TABLE terminations ADD COLUMN decimo_meses INTEGER DEFAULT 0",
        "ALTER TABLE terminations ADD COLUMN decimo_ja_pago NUMERIC(10,2) DEFAULT 0",
        "ALTER TABLE terminations ADD COLUMN notice_reduction VARCHAR(20)",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # coluna já existe
        # Corrige rescisões com data futura que foram marcadas como concluída indevidamente
        try:
            from datetime import date
            today = date.today().isoformat()
            conn.execute(text(
                "UPDATE terminations SET status = 'pendente' WHERE status = 'concluida' AND termination_date > :today"
            ), {"today": today})
            conn.commit()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.DATABASE_URL.startswith("sqlite"):
        _run_sqlite_migrations()
    logger.info(f"Sistema de RH iniciado — ambiente: {settings.ENVIRONMENT}")
    yield


app = FastAPI(
    title="Sistema de RH",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
)

# ── Rate limiter ───────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS — usa lista do .env em vez de wildcard ────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Headers de segurança HTTP ──────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if not settings.is_development:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/versao")
def versao():
    """Endpoint para auto-update do app desktop."""
    return {
        "version": settings.APP_VERSION,
        "download_url": None,
    }
