from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.database import Base, engine
import app.models  # noqa: F401 — garante que todos os modelos sejam registrados


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
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
