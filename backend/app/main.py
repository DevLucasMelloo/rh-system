from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.database import Base, engine
import app.models  # noqa: F401 — garante que todos os modelos sejam registrados


def _run_migrations():
    """Aplica colunas novas em tabelas existentes (SQLite não tem ADD COLUMN IF NOT EXISTS)."""
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
    _run_migrations()
    logger.info(f"Sistema de RH iniciado — ambiente: {settings.ENVIRONMENT}")
    yield


app = FastAPI(
    title="Sistema de RH",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    # Em produção, desabilitar docs públicos
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/versao")
def versao():
    """Endpoint para auto-update do app desktop."""
    return {
        "version": settings.APP_VERSION,
        "download_url": None,
    }
