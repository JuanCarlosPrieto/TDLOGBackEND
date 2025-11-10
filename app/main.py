from fastapi import FastAPI
from app.api.v1 import auth

app = FastAPI(title="Checkers API")

app.include_router(auth.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
