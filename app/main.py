from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.db.session import SessionLocal
from app.db.seed_categories import seed_global_categories
import os
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: seed global categories on startup."""
    db = SessionLocal()
    try:
        seed_global_categories(db)
    finally:
        db.close()
    yield


# Create static directory for avatars if not exists
os.makedirs("app/static/avatars", exist_ok=True)
app = FastAPI(
    title="Seharta API",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local testing (especially Flutter Web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def root():
    return {
        "message": "Seharta API is running"
    }


app.include_router(
    api_router,
    prefix="/api/v1"
)