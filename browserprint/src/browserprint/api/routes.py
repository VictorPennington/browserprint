"""Route definitions for the local FastAPI server."""

import logging
from collections.abc import Callable
from uuid import uuid4

from fastapi import APIRouter

from .downloads.service import format_url_for_log
from .job_queue import DOWNLOAD_QUEUE
from .schemas import PrintJobsRequest, PrintRequest

router = APIRouter()
logger = logging.getLogger("browserprint.api.routes")


def _get_print_override() -> str | None:
    return None


def set_print_override_provider(fn: Callable[[], str | None]) -> None:
    """Register a callable that returns an override printerCommand or None."""
    global _get_print_override
    _get_print_override = fn


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
    effective_command = _get_print_override() or request.printerCommand
    logger.info(
        "Request-> /print to: %s, CustomerNumber=%s, InvoiceNumber=%s",
        format_url_for_log(request.pdfUrl),
        request.customerNumber,
        request.invoiceNumber,
    )
    if effective_command != request.printerCommand:
        logger.info(
            "printerCommand overridden: %r -> %r",
            request.printerCommand,
            effective_command,
        )
    DOWNLOAD_QUEUE.put(
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
        effective_command = override_command or job.printerCommand
        logger.info(
            "Request-> /print/jobs job_request_id=%s to: %s, Inv.Number: %s, CustomerNumber: %s",
            job_request_id,
            format_url_for_log(job.pdfUrl),
            invoice_number,
            customer_number,
        )
        if effective_command != job.printerCommand:
            logger.info(
                "printerCommand overridden: %r -> %r",
                job.printerCommand,
                effective_command,
            )
        DOWNLOAD_QUEUE.put(
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
