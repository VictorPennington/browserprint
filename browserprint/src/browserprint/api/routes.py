"""Route definitions for the local FastAPI server."""

import logging
import queue
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from browserprint.settings import DEBUG_OUTPUT_DIR, SUMATRA_PATH

from .pdf_fetcher import PDFDownloadError, fetch_pdf

router = APIRouter()
logger = logging.getLogger("browserprint.api.routes")

_DEBUG_OUTPUT_DIR = DEBUG_OUTPUT_DIR
_DOWNLOAD_QUEUE: queue.Queue = queue.Queue()


def _download_worker() -> None:
    while True:
        request_id, pdf_url, printer_command = _DOWNLOAD_QUEUE.get()
        try:
            _run_single_download_job(
                request_id=request_id,
                pdf_url=pdf_url,
                printer_command=printer_command,
            )
        finally:
            _DOWNLOAD_QUEUE.task_done()


_download_worker_thread = threading.Thread(
    target=_download_worker, daemon=True, name="download-worker"
)
_download_worker_thread.start()

_SUMATRA_PDF_PATH = SUMATRA_PATH


def _format_url_for_log(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path


class PrintRequest(BaseModel):
    pdfUrl: str = Field(min_length=1)
    printCommand: str = Field(min_length=1)

    @field_validator("pdfUrl")
    @classmethod
    def validate_url_scheme(cls, value: str) -> str:
        lowered = value.lower().strip()
        if not lowered.startswith(("http://", "https://")):
            raise ValueError("pdfUrl must use http:// or https://")
        return value.strip()


class PrintJobsRequest(BaseModel):
    jobs: list[PrintRequest] = Field(min_length=1)


@router.get("/")
def root() -> dict[str, str]:
    return {"message": "hello world"}


#  ROUTER OPTIONS IS FOR HANDLING CORS
@router.options("/print")
def options_print() -> dict:
    return {}


#  ROUTER OPTIONS IS FOR HANDLING CORS
@router.options("/print/jobs")
def options_print_jobs() -> dict:
    return {}


@router.post("/print", status_code=202)
def print_document(request: PrintRequest) -> dict[str, str]:
    request_id = uuid4().hex
    logger.info(
        "Request-> /print to: %s",
        _format_url_for_log(request.pdfUrl),
    )
    _DOWNLOAD_QUEUE.put((request_id, request.pdfUrl, request.printCommand))

    return {
        "status": "accepted",
        "requestId": request_id,
        "message": "Request validated and queued.",
    }


@router.post("/print/jobs", status_code=202)
def print_document_jobs(request: PrintJobsRequest) -> dict[str, str]:
    request_id = uuid4().hex
    logger.info(
        "Request-> /print/jobs request_id=%s jobs_count=%s",
        request_id,
        len(request.jobs),
    )
    for index, job in enumerate(request.jobs, start=1):
        job_request_id = f"{request_id}-{index}"
        _DOWNLOAD_QUEUE.put((job_request_id, job.pdfUrl, job.printCommand))

    return {
        "status": "accepted",
        "requestId": request_id,
        "acceptedJobs": str(len(request.jobs)),
        "message": "Jobs validated and queued for background download.",
    }


def _run_single_download_job(
    request_id: str, pdf_url: str, printer_command: str
) -> None:
    try:
        _DEBUG_OUTPUT_DIR.mkdir(exist_ok=True)
        output_path = _resolve_output_path(pdf_url)
        logger.info("download started for: \n     %s", _format_url_for_log(pdf_url))
        pdf_bytes = fetch_pdf(pdf_url)
        output_path.write_bytes(pdf_bytes)
        logger.info(
            "Download successful!\n     filename= %s \n     command= %s",
            output_path,
            printer_command,
        )
    except PDFDownloadError as exc:
        logger.error("download_failed request_id=%s reason=%s", request_id, exc)
    except OSError as exc:
        logger.error("download_save_failed request_id=%s reason=%s", request_id, exc)
    except Exception:
        logger.exception("download_unexpected_failure request_id=%s", request_id)


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
