from fastapi import FastAPI

from .ai_item_reviews import init_ai_item_review_db, router as ai_item_review_router
from .ai_status import router as ai_status_router
from .database import init_db
from .router import router

app = FastAPI(
    title="Data Integrity Case File",
    description="Portfolio-safe ALCOA+ investigation workspace — synthetic data only.",
    version="0.1.0",
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    init_ai_item_review_db()


app.include_router(router)
app.include_router(ai_status_router)
app.include_router(ai_item_review_router)
