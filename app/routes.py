from fastapi import APIRouter
from app.data import Academic_majors, Creative_majors
from app.services import search_by_name

router = APIRouter()

@router.get("/academic-majors")
def get_academic_majors():
    return Academic_majors

@router.get("/creative-majors")
def get_creative_majors():
    return Creative_majors

@router.get("/search")
def search(name: str):
    return search_by_name(name)