import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_pool, close_pool
from app.routers import webhooks, health, demo

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.elevenlabs_webhook_secret:
        raise RuntimeError("ELEVENLABS_WEBHOOK_SECRET must be set")
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="Memory Autopilot", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)
app.include_router(health.router)
app.include_router(demo.router)
