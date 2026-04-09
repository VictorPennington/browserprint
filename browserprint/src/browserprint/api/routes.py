"""Route definitions for the local FastAPI server."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from .pdf_fetcher import PDFDownloadError, fetch_pdf
from .print_executor import PrintExecutionError, run_sumatra_print

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
    filename: str

    @field_validator("pdfUrl")
    @classmethod
    def validate_url_scheme(cls, value: str) -> str:
        lowered = value.lower().strip()
        if not lowered.startswith(("http://", "https://")):
            raise ValueError("pdfUrl must use http:// or https://")
        return value.strip()

    @field_validator("filename")
    @classmethod
    def normalize_filename(cls, value: str) -> str:
        filename = Path(value).name.strip()
        if not filename:
            raise ValueError("filename cannot be empty")
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"
        return filename


@router.get("/")
def root() -> dict[str, str]:
    return {"message": "hello world"}


@router.options("/print")
def options_print() -> dict:
    return {}


@router.post("/print")
def print_document(request: PrintRequest) -> dict[str, str]:
    _DEBUG_OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = _DEBUG_OUTPUT_DIR / request.filename

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

    try:
        run_sumatra_print(
            sumatra_path=_SUMATRA_PDF_PATH,
            printer_command=request.printerCommand,
            output_path=output_path,
        )
    except PrintExecutionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "status": "printed",
        "filename": request.filename,
    }
