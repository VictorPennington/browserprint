"""FastAPI server setup for local machine requests."""

import json
import logging
import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from browserprint.settings import ALLOWED_ORIGINS, LOCAL_API_HOST, LOCAL_API_PORT

from .routes import router

logger = logging.getLogger("browserprint.api.server")


def create_app() -> FastAPI:
    api = FastAPI(title="BrowserPrint Local API")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-TOKEN"],
    )

    def _serialize_error(error: dict) -> dict:
        """Convert error dict to JSON-serializable format."""
        result = {}
        for key, value in error.items():
            if key == "ctx" and isinstance(value, dict):
                # Convert ctx values to strings if they're exceptions
                result[key] = {
                    k: str(v) if isinstance(v, Exception) else v
                    for k, v in value.items()
                }
            else:
                result[key] = str(value) if isinstance(value, Exception) else value
        return result

    @api.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Log detailed validation errors."""
        errors = [_serialize_error(err) for err in exc.errors()]
        logger.error(
            "Validation error on %s %s: %s",
            request.method,
            request.url.path,
            json.dumps(errors, indent=2),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": errors},
        )

    @api.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %s (%.1f ms)",
            request.method,
            request.url,
            response.status_code,
            elapsed_ms,
        )
        return response

    api.include_router(router)
    return api


app = create_app()


def run_local_server(host: str = LOCAL_API_HOST, port: int = LOCAL_API_PORT) -> None:
    logger.info("Starting local API server on %s:%s", host, port)
    uvicorn.run(app, host=host, port=port)
