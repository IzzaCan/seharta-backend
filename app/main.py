from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router


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


@app.get("/")
def root():
    return {
        "message": "Seharta API is running"
    }


app.include_router(
    api_router,
    prefix="/api/v1"
)