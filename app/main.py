from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .ai_item_reviews import init_ai_item_review_db, router as ai_item_review_router
from .ai_status import router as ai_status_router
from .database import init_db
from .router import router
from .security import ApiKeyMiddleware, RateLimitMiddleware

app = FastAPI(
    title="Data Integrity Case File",
    description=(
        "Portfolio-safe ALCOA+ investigation workspace — synthetic data only. "
        "Requires header X-API-Key on all endpoints except /health."
    ),
    version="0.2.0",
)

# Order: last added is outermost. Rate limit then API key then CORS.
app.add_middleware(ApiKeyMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    init_ai_item_review_db()


app.include_router(router)
app.include_router(ai_status_router)
app.include_router(ai_item_review_router)
