from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .ai_item_reviews import router as ai_item_review_router
from .ai_status import router as ai_status_router
from .database import disconnect, init_db
from .router import router
from .security import ApiKeyMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()  # schema + open shared connection
    try:
        yield
    finally:
        await disconnect()


app = FastAPI(
    title="Data Integrity Case File",
    description=(
        "Portfolio-safe ALCOA+ investigation workspace — synthetic data only. "
        "Requires header X-API-Key on all endpoints except /health. "
        "Shared aiosqlite connection (WAL) + async Ollama client."
    ),
    version="0.4.1",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ApiKeyMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(ai_status_router)
app.include_router(ai_item_review_router)
