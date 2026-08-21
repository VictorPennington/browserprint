"""Background worker threads and job queues for download and print pipeline."""

import logging
import queue
import threading

from browserprint.settings import PDFTOPRINTER_PATH

from .downloads.service import run_download_job
from .prints.executor import PrintExecutionError
from .prints.pdftoprinter_executor import run_pdftoprinter_print

logger = logging.getLogger("browserprint.api.job_queue")

DOWNLOAD_QUEUE: queue.Queue = queue.Queue()
PRINT_QUEUE: queue.Queue = queue.Queue()

_PDFTOPRINTER_PATH = PDFTOPRINTER_PATH


def _download_worker() -> None:
    while True:
        request_id, pdf_url, printer_command, customer_number, invoice_number = (
            DOWNLOAD_QUEUE.get()
        )
        try:
            run_download_job(
                request_id=request_id,
                pdf_url=pdf_url,
                printer_command=printer_command,
                customer_number=customer_number,
                invoice_number=invoice_number,
                print_queue=PRINT_QUEUE,
            )
        finally:
            DOWNLOAD_QUEUE.task_done()


def _print_worker() -> None:
    while True:
        request_id, output_path, printer_command = PRINT_QUEUE.get()
        try:
            run_pdftoprinter_print(_PDFTOPRINTER_PATH, printer_command, output_path)
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
            PRINT_QUEUE.task_done()


_download_worker_thread = threading.Thread(
    target=_download_worker, daemon=True, name="download-worker"
)
_download_worker_thread.start()

_print_worker_thread = threading.Thread(
    target=_print_worker, daemon=True, name="print-worker"
)
_print_worker_thread.start()
