"""FastAPI server setup for local machine requests."""

import logging
import time

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

logger = logging.getLogger("browserprint.api.server")

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
    load_dotenv()
    api = FastAPI(title="BrowserPrint Local API")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=_ALLOWED_ORIGINS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-TOKEN"],
    )

    @api.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %s (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    api.include_router(router)
    return api


app = create_app()


def run_local_server(host: str = "127.0.0.1", port: int = 8003) -> None:
    logger.info("Starting local API server on %s:%s", host, port)
    uvicorn.run(app, host=host, port=port)
