"""Route definitions for the local FastAPI server."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root() -> dict[str, str]:
    return {"message": "hello world"}
