"""FastAPI server setup for local machine requests."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

# Origins allowed to call this local API from a browser page.
_ALLOWED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8003",
    "http://127.0.0.1",
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:8003",
]


def create_app() -> FastAPI:
    api = FastAPI(title="BrowserPrint Local API")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=_ALLOWED_ORIGINS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-TOKEN"],
    )
    api.include_router(router)
    return api


app = create_app()


def run_local_server(host: str = "127.0.0.1", port: int = 8003) -> None:
    uvicorn.run(app, host=host, port=port)
