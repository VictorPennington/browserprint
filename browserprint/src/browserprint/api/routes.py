"""Route definitions for the local FastAPI server."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class PrintRequest(BaseModel):
    content: str


@router.get("/")
def root() -> dict[str, str]:
    return {"message": "hello world"}


@router.options("/print")
def options_print() -> dict:
    return {}


@router.post("/print")
def print_document(request: PrintRequest) -> dict[str, str]:
    # Print to console
    print("Hello-World")
    return {"response": "hello-world"}
