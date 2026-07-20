from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, documents, edges, scenarios
from app.services.hero_seed import initialize_database

LOCAL_FRONTEND_ORIGIN = "http://localhost:3000"


def allowed_origins(frontend_origin: str) -> list[str]:
    configured = frontend_origin.rstrip("/")
    if configured == LOCAL_FRONTEND_ORIGIN:
        return [LOCAL_FRONTEND_ORIGIN]
    return [LOCAL_FRONTEND_ORIGIN, configured]


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="FragilityGraph API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(settings.frontend_origin),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(edges.router)
app.include_router(scenarios.router)
app.include_router(chat.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
