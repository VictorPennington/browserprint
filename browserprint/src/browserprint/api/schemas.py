"""Pydantic request/response schemas for the BrowserPrint API."""

from pydantic import BaseModel, Field, field_validator


class PrintRequest(BaseModel):
    pdfUrl: str = Field(min_length=1)
    printerCommand: str = Field(min_length=1)
    customerNumber: str | int | None = None
    invoiceNumber: str | int | None = None

    @field_validator("pdfUrl")
    @classmethod
    def validate_url_scheme(cls, value: str) -> str:
        lowered = value.lower().strip()
        if not lowered.startswith(("http://", "https://")):
            raise ValueError("pdfUrl must use http:// or https://")
        return value.strip()

    @field_validator("printerCommand")
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
