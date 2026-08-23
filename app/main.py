from fastapi import FastAPI
from .database import init_db
from .router import router

app = FastAPI(
    title="Data Integrity Case File",
    description="Portfolio-safe ALCOA+ investigation workspace — synthetic data only.",
    version="0.1.0",
)


@app.on_event("startup")
def startup():
    init_db()


app.include_router(router)
