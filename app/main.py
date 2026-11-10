from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text

from app.core.config import get_settings, configure_langsmith
from app.core.database import engine
from app.core.redis import redis_client
from app.voice.routes import router as voice_router
from app.voice.websocket import router as websocket_router
from app.Auth.routes import router as auth_router
from app.routes.customer_route import router as customer_router
from app.routes.call_route import router as call_router
from app.routes.call_insight_route import router as call_insight_router
from app.routes.dashboard_route import router as dashboard_router

settings = get_settings()
configure_langsmith(settings)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting CustomerCare AI Agent...")
    yield
    await redis_client.aclose()
    await engine.dispose()
    print("Infrastructure connections closed.")

app = FastAPI(
    title=settings.app_name,
    description="Voice AI Customer Care and Sales Agent",
    version="0.1.0",
    lifespan=lifespan,
)

# ✅ ADD CORS MIDDLEWARE
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        # Add your production domains here
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

app.include_router(voice_router)
app.include_router(websocket_router)
app.include_router(auth_router)
app.include_router(customer_router)
app.include_router(call_router)
app.include_router(call_insight_router)
app.include_router(dashboard_router)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.app_env,
    }

@app.get("/ready")
async def readiness_check():
    postgres_ready = False
    redis_ready = False

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        postgres_ready = True
    except Exception:
        postgres_ready = False

    try:
        redis_ready = bool(await redis_client.ping())
    except Exception:
        redis_ready = False

    ready = postgres_ready and redis_ready

    response = {
        "status": "ready" if ready else "not_ready",
        "environment": settings.app_env,
        "dependencies": {
            "postgres": "up" if postgres_ready else "down",
            "redis": "up" if redis_ready else "down",
        },
    }

    if not ready:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=response)

    return response