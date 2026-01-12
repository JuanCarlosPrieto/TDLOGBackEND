from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth
from app.api.v1 import matchmaking
from app.api.v1 import match_ws
from app.api.v1 import match_history

app = FastAPI(title="Checkers API")

# Only local for now
origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(matchmaking.router, prefix="/api/v1")
app.include_router(match_ws.router, prefix="/api/v1")
app.include_router(match_history.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
