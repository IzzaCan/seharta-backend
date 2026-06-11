from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
import os
from fastapi.staticfiles import StaticFiles

# Create static directory for avatars if not exists
os.makedirs("app/static/avatars", exist_ok=True)
app = FastAPI(
    title="Seharta API",
    version="1.0.0"
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