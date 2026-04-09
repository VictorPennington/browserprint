"""Route definitions for the local FastAPI server."""

from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from .pdf_fetcher import PDFDownloadError, fetch_pdf

router = APIRouter()

_DEBUG_OUTPUT_DIR = Path.home() / "Desktop" / "debug_pdfs"
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


@router.post("/print")
def print_document(request: PrintRequest) -> dict[str, str]:
    _DEBUG_OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = _resolve_output_path(request.pdfUrl)

    try:
        pdf_bytes = fetch_pdf(request.pdfUrl)
    except PDFDownloadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    try:
        output_path.write_bytes(pdf_bytes)
    except OSError as exc:
        raise HTTPException(
            status_code=500, detail="Failed to save downloaded PDF"
        ) from exc

    return {
        "status": "downloaded",
        "filename": output_path.name,
        "message": "PDF downloaded and saved locally. Printing step is not enabled yet.",
    }


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
