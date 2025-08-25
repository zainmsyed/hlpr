"""
Example router to validate project structure.
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def read_example():
    return {"message": "Example endpoint works!"}
