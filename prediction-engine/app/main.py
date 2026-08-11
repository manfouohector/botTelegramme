"""
main.py — Point d'entrée FastAPI pour le DevMind Prediction Engine
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
from loguru import logger
import time

load_dotenv()

app = FastAPI(
    title="DevMind Prediction Engine",
    description="Moteur de prédictions sportives IA (Poisson + XGBoost)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---- Middleware de logging ----
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    logger.debug(f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)")
    return response


# ---- Middleware d'authentification interne ----
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

@app.middleware("http")
async def verify_internal_api_key(request: Request, call_next):
    # Exclure la route /health de l'authentification
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)

    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != INTERNAL_API_KEY:
        return JSONResponse(
            status_code=401,
            content={"error": "Clé API interne invalide ou manquante"}
        )
    return await call_next(request)


from app.api import predictions

# ---- Routes ----
app.include_router(predictions.router)

@app.get("/health", tags=["Système"])
async def health_check():
    return {
        "status": "ok",
        "service": "devmind-prediction-engine",
        "version": "1.0.0",
    }


# ---- Événements de démarrage ----
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 DevMind Prediction Engine démarré")
    logger.info(f"   Environnement : {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"   Port : {os.getenv('PYTHON_PORT', 8000)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PYTHON_PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="debug",
    )
