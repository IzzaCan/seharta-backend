from fastapi import FastAPI

from app.api.v1.router import api_router


app = FastAPI(
    title="Seharta API",
    version="1.0.0"
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