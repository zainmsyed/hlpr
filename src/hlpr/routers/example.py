"""Example router migrated to new hlpr package."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def read_example():
    return {"message": "Example endpoint works!"}
