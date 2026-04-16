"""Download pipeline logic: filename building, path resolution, and job execution."""

import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from browserprint.settings import DEBUG_OUTPUT_DIR

from .pdf_fetcher import PDFDownloadError, fetch_pdf

logger = logging.getLogger("browserprint.api.download_service")

_DEBUG_OUTPUT_DIR = DEBUG_OUTPUT_DIR


def _is_printing_disabled() -> bool:
    return False


def set_printing_disabled_provider(fn) -> None:
    """Register a callable that returns True when printing should be suppressed."""
    global _is_printing_disabled
    _is_printing_disabled = fn


def format_url_for_log(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path


def build_download_filename(
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


def resolve_output_path(
    pdf_url: str,
    customer_number: str | int | None,
    invoice_number: str | int | None,
) -> Path:
    output_path = _DEBUG_OUTPUT_DIR / build_download_filename(
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


def run_download_job(
    request_id: str,
    pdf_url: str,
    printer_command: str,
    customer_number: str | int | None,
    invoice_number: str | int | None,
    print_queue,
) -> None:
    """Download a PDF and enqueue it for printing. Logs all outcomes."""
    try:
        _DEBUG_OUTPUT_DIR.mkdir(exist_ok=True)
        output_path = resolve_output_path(pdf_url, customer_number, invoice_number)
        logger.info("download started for: \n     %s", format_url_for_log(pdf_url))
        pdf_bytes = fetch_pdf(pdf_url)
        output_path.write_bytes(pdf_bytes)
        if _is_printing_disabled():
            logger.info(
                "Download successful (printing disabled).\n     filename= %s",
                output_path,
            )
        else:
            logger.info(
                "Download successful, queued for print!\n     filename= %s \n     command= %s",
                output_path,
                printer_command,
            )
        if not _is_printing_disabled():
            print_queue.put((request_id, output_path, printer_command))
    except PDFDownloadError as exc:
        logger.error("download_failed request_id=%s reason=%s", request_id, exc)
    except OSError as exc:
        logger.error("download_save_failed request_id=%s reason=%s", request_id, exc)
    except Exception:
        logger.exception("download_unexpected_failure request_id=%s", request_id)
