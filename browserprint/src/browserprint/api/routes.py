"""Route definitions for the local FastAPI server."""

import base64
import subprocess
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

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
    printerCommand: str = ""
    filename: str
    contentType: str
    contentEncoding: str
    content: str


@router.get("/")
def root() -> dict[str, str]:
    return {"message": "hello world"}


@router.options("/print")
def options_print() -> dict:
    return {}


@router.post("/print")
def print_document(request: PrintRequest) -> dict[str, str]:
    _DEBUG_OUTPUT_DIR.mkdir(exist_ok=True)

    pdf_bytes = base64.b64decode(request.content)
    output_path = _DEBUG_OUTPUT_DIR / request.filename
    output_path.write_bytes(pdf_bytes)

    # Build simple command string: exe + options + output path
    command_string = f'"{_SUMATRA_PDF_PATH}" {request.printerCommand} "{output_path}"'

    print(f"Executing: {command_string}")

    result = subprocess.run(
        command_string,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
    )

    print(
        f"Saved PDF: {output_path} ({len(pdf_bytes)} bytes) - Return code: {result.returncode}"
    )

    return {
        "status": "saved",
    }
