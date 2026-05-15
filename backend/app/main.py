"""
Entrypoint da aplicação FastAPI.

Rode com:

    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

A app expõe automaticamente:
* /docs       → Swagger UI
* /redoc      → Redoc
* /openapi.json
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import router as api_router
from app.utils.logger import configure_logging, get_logger

configure_logging()
log = get_logger("app.main")

app = FastAPI(
    title="OLT Config Converter Engine",
    description=(
        "Backend para conversão modular de configurações de OLTs entre "
        "vendors (Fiberhome, ZTE, Huawei, Datacom). "
        "Arquitetura: CONFIG ORIGEM → MODELO INTERNO → CONFIG DESTINO."
    ),
    version=__version__,
)

# CORS aberto para o frontend Vite (porta 5173) — ajuste em produção.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.on_event("startup")
async def on_startup() -> None:
    log.info("backend_started", version=__version__)
