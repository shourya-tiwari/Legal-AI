import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("legalai.main")

# Import route modules
from .routes import upload
from .routes import rewrite
from .routes import map, ask
from .routes import risk_radar
from .routes import contextualize
from .routes import nlp
from .routes import kg
from .routes import agents

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info(
        "Startup complete. auth_required=%s database=%s",
        settings.AUTH_REQUIRED,
        settings.DATABASE_URL.split("://")[0],
    )
    yield


app = FastAPI(title="LegalAI Contract Analyzer Backend", version="0.1.0", lifespan=lifespan)

# ---- Exception Handler ----
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Invalid request body. Ensure JSON meets endpoint requirements.",
            "details": exc.errors(),
        },
    )

# ---- Routers ----
app.include_router(upload.router, prefix="/api", tags=["extract"])
app.include_router(rewrite.router, prefix="/api", tags=["rewrite"])
app.include_router(map.router, prefix="/api", tags=["timeline"])
app.include_router(ask.router, prefix="/api", tags=["chatbot"])
app.include_router(risk_radar.router, prefix="/api", tags=["risk"])
app.include_router(contextualize.router, prefix="/api", tags=["contextualizer"])
app.include_router(nlp.router, prefix="/api", tags=["nlp"])
app.include_router(kg.router, prefix="/api", tags=["knowledge-graph"])
app.include_router(agents.router, prefix="/api", tags=["agents"])

# ---- Health Endpoint ----
@app.get("/", tags=["health"])
async def root():
    return {"message": "LegalAI Contract Analyser backend is running."}

# ---- CORS ----
# No cookie/session-based auth exists yet, so credentials are not needed.
# A wildcard origin with allow_credentials=True is invalid per the CORS spec
# (browsers reject it); allow_credentials=False makes the wildcard valid.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)
