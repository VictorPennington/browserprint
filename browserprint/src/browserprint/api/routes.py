"""Route definitions for the local FastAPI server."""

import logging
import queue
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from browserprint.settings import DEBUG_OUTPUT_DIR, SUMATRA_PATH

from .pdf_fetcher import PDFDownloadError, fetch_pdf
from .print_executor import PrintExecutionError, run_sumatra_print

router = APIRouter()
logger = logging.getLogger("browserprint.api.routes")

_DEBUG_OUTPUT_DIR = DEBUG_OUTPUT_DIR
_DOWNLOAD_QUEUE: queue.Queue = queue.Queue()
_PRINT_QUEUE: queue.Queue = queue.Queue()


def _get_print_override() -> str | None:
    return None


def set_print_override_provider(fn: Callable[[], str | None]) -> None:
    """Register a callable that returns an override printCommand or None."""
    global _get_print_override
    _get_print_override = fn


def _download_worker() -> None:
    while True:
        request_id, pdf_url, printer_command, customer_number, invoice_number = (
            _DOWNLOAD_QUEUE.get()
        )
        try:
            _run_single_download_job(
                request_id=request_id,
                pdf_url=pdf_url,
                printer_command=printer_command,
                customer_number=customer_number,
                invoice_number=invoice_number,
            )
        finally:
            _DOWNLOAD_QUEUE.task_done()


def _print_worker() -> None:
    while True:
        request_id, output_path, printer_command = _PRINT_QUEUE.get()
        try:
            run_sumatra_print(_SUMATRA_PDF_PATH, printer_command, output_path)
            logger.info(
                "Print successful! request_id=%s file=%s",
                request_id,
                output_path.name,
            )
        except PrintExecutionError as exc:
            logger.error("print_failed request_id=%s reason=%s", request_id, exc)
        except Exception:
            logger.exception("print_unexpected_failure request_id=%s", request_id)
        finally:
            _PRINT_QUEUE.task_done()


_download_worker_thread = threading.Thread(
    target=_download_worker, daemon=True, name="download-worker"
)
_download_worker_thread.start()

_print_worker_thread = threading.Thread(
    target=_print_worker, daemon=True, name="print-worker"
)
_print_worker_thread.start()

_SUMATRA_PDF_PATH = SUMATRA_PATH


def _format_url_for_log(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path


def _build_download_filename(
    pdf_url: str,
    customer_number: str | int | None,
    invoice_number: str | int | None,
) -> str:
    parsed = urlparse(pdf_url)
    endpoint_name = Path(parsed.path).stem.strip() or "downloaded"
    customer = str(customer_number).strip() if customer_number is not None else ""
    invoice = str(invoice_number).strip() if invoice_number is not None else ""
    customer = customer or "_"
    invoice = invoice or "_"
    timestamp = datetime.now().strftime("%Y_%m_%d_%H%M")
    return f"{timestamp}_{customer}_{invoice}_{endpoint_name}.pdf"


class PrintRequest(BaseModel):
    pdfUrl: str = Field(min_length=1)
    printCommand: str = Field(min_length=1)
    customerNumber: str | int | None = None
    invoiceNumber: str | int | None = None

    @field_validator("pdfUrl")
    @classmethod
    def validate_url_scheme(cls, value: str) -> str:
        lowered = value.lower().strip()
        if not lowered.startswith(("http://", "https://")):
            raise ValueError("pdfUrl must use http:// or https://")
        return value.strip()

    @field_validator("printCommand")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("field cannot be empty")
        return normalized


class PrintJobsRequest(BaseModel):
    jobs: list[PrintRequest] = Field(min_length=1)
    customerNumber: str | int | None = None
    invoiceNumber: str | int | None = None


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
    effective_command = _get_print_override() or request.printCommand
    logger.info(
        "Request-> /print to: %s, CustomerNumber=%s, InvoiceNumber=%s",
        _format_url_for_log(request.pdfUrl),
        request.customerNumber,
        request.invoiceNumber,
    )
    if effective_command != request.printCommand:
        logger.info(
            "printCommand overridden: %r -> %r", request.printCommand, effective_command
        )
    _DOWNLOAD_QUEUE.put(
        (
            request_id,
            request.pdfUrl,
            effective_command,
            request.customerNumber,
            request.invoiceNumber,
        )
    )

    return {
        "status": "accepted",
        "requestId": request_id,
        "message": "Request validated and queued.",
    }


@router.post("/print/jobs", status_code=202)
def print_document_jobs(request: PrintJobsRequest) -> dict[str, str]:
    request_id = uuid4().hex
    customer_number = request.customerNumber
    invoice_number = request.invoiceNumber
    logger.info(
        "Request-> /print/jobs request_id=%s Customer Number=%s, Invoice Number=%s",
        request_id,
        customer_number,
        invoice_number,
    )
    override_command = _get_print_override()
    for index, job in enumerate(request.jobs, start=1):
        job_request_id = f"{request_id}-{index}"
        effective_command = override_command or job.printCommand
        logger.info(
            "Request-> /print/jobs job_request_id=%s to: %s, Inv.Number: %s, CustomerNumber: %s",
            job_request_id,
            _format_url_for_log(job.pdfUrl),
            invoice_number,
            customer_number,
        )
        if effective_command != job.printCommand:
            logger.info(
                "printCommand overridden: %r -> %r", job.printCommand, effective_command
            )
        _DOWNLOAD_QUEUE.put(
            (
                job_request_id,
                job.pdfUrl,
                effective_command,
                customer_number,
                invoice_number,
            )
        )

    return {
        "status": "accepted",
        "requestId": request_id,
        "acceptedJobs": str(len(request.jobs)),
        "message": "Jobs validated and queued for background download.",
    }


def _run_single_download_job(
    request_id: str,
    pdf_url: str,
    printer_command: str,
    customer_number: str | int | None,
    invoice_number: str | int | None,
) -> None:
    try:
        _DEBUG_OUTPUT_DIR.mkdir(exist_ok=True)
        output_path = _resolve_output_path(pdf_url, customer_number, invoice_number)
        logger.info("download started for: \n     %s", _format_url_for_log(pdf_url))
        pdf_bytes = fetch_pdf(pdf_url)
        output_path.write_bytes(pdf_bytes)
        logger.info(
            "Download successful, queued for print!\n     filename= %s \n     command= %s",
            output_path,
            printer_command,
        )
        _PRINT_QUEUE.put((request_id, output_path, printer_command))
    except PDFDownloadError as exc:
        logger.error("download_failed request_id=%s reason=%s", request_id, exc)
    except OSError as exc:
        logger.error("download_save_failed request_id=%s reason=%s", request_id, exc)
    except Exception:
        logger.exception("download_unexpected_failure request_id=%s", request_id)


def _resolve_output_path(
    pdf_url: str,
    customer_number: str | int | None,
    invoice_number: str | int | None,
) -> Path:
    output_path = _DEBUG_OUTPUT_DIR / _build_download_filename(
        pdf_url, customer_number, invoice_number
    )
    if not output_path.exists():
        return output_path

    stem = output_path.stem
    suffix = output_path.suffix or ".pdf"
    counter = 2
    while True:
        candidate = _DEBUG_OUTPUT_DIR / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
