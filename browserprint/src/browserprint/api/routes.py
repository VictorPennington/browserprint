"""Route definitions for the local FastAPI server."""

import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field, field_validator

from .pdf_fetcher import PDFDownloadError, fetch_pdf

router = APIRouter()
logger = logging.getLogger("browserprint.api.routes")

_DEBUG_OUTPUT_DIR = Path.home() / "Desktop" / "debug_pdfs"
_MAX_CONCURRENT_DOWNLOADS = int(os.getenv("BROWSERPRINT_MAX_CONCURRENT_DOWNLOADS", "8"))
_DOWNLOAD_SEMAPHORE = threading.BoundedSemaphore(value=_MAX_CONCURRENT_DOWNLOADS)
_SUMATRA_PDF_PATH = (
    Path(__file__).resolve().parents[1]
    / "resources"
    / "vendor"
    / "sumatrapdf"
    / "SumatraPDF-3.6-64.exe"
)


class PrintRequest(BaseModel):
    pdfUrl: str = Field(min_length=1)
    printerCommand: str = Field(min_length=1)

    @field_validator("pdfUrl")
    @classmethod
    def validate_url_scheme(cls, value: str) -> str:
        lowered = value.lower().strip()
        if not lowered.startswith(("http://", "https://")):
            raise ValueError("pdfUrl must use http:// or https://")
        return value.strip()


@router.get("/")
def root() -> dict[str, str]:
    return {"message": "hello world"}


@router.options("/print")
def options_print() -> dict:
    return {}


@router.post("/print", status_code=202)
def print_document(
    request: PrintRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    if not _try_acquire_download_slot():
        raise HTTPException(
            status_code=503,
            detail="Download queue is full. Please retry shortly.",
        )

    request_id = uuid4().hex
    logger.info(
        "download_request_accepted request_id=%s pdf_url=%s",
        request_id,
        request.pdfUrl,
    )
    background_tasks.add_task(
        _run_download_task,
        request_id=request_id,
        pdf_url=request.pdfUrl,
        printer_command=request.printerCommand,
    )

    return {
        "status": "accepted",
        "requestId": request_id,
        "message": "Request validated and queued for background download.",
    }


def _run_download_task(request_id: str, pdf_url: str, printer_command: str) -> None:
    try:
        _DEBUG_OUTPUT_DIR.mkdir(exist_ok=True)
        output_path = _resolve_output_path(pdf_url)
        logger.info("download_started request_id=%s", request_id)
        pdf_bytes = fetch_pdf(pdf_url)
        output_path.write_bytes(pdf_bytes)
        logger.info(
            "download_saved request_id=%s filename=%s printer_command=%s",
            request_id,
            output_path.name,
            printer_command,
        )
    except PDFDownloadError as exc:
        logger.error("download_failed request_id=%s reason=%s", request_id, exc)
    except OSError as exc:
        logger.error("download_save_failed request_id=%s reason=%s", request_id, exc)
    except Exception:
        logger.exception("download_unexpected_failure request_id=%s", request_id)
    finally:
        _DOWNLOAD_SEMAPHORE.release()


def _try_acquire_download_slot() -> bool:
    return _DOWNLOAD_SEMAPHORE.acquire(blocking=False)


def _resolve_output_path(pdf_url: str) -> Path:
    parsed = urlparse(pdf_url)
    candidate = Path(parsed.path).name.strip() or "downloaded.pdf"
    if not candidate.lower().endswith(".pdf"):
        candidate = f"{candidate}.pdf"

    output_path = _DEBUG_OUTPUT_DIR / candidate
    if output_path.exists():
        stem = output_path.stem
        suffix = output_path.suffix or ".pdf"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = _DEBUG_OUTPUT_DIR / f"{stem}-{timestamp}{suffix}"

    return output_path
