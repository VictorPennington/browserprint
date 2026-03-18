"""FastAPI server setup for local machine requests."""

import uvicorn
from fastapi import FastAPI

from .routes import router


def create_app() -> FastAPI:
    api = FastAPI(title="BrowserPrint Local API")
    api.include_router(router)
    return api


app = create_app()


def run_local_server(host: str = "127.0.0.1", port: int = 8003) -> None:
    uvicorn.run(app, host=host, port=port)
