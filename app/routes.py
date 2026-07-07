from fastapi import APIRouter
from app.data import majors, Creative_majors

router = APIRouter()

@router.get("/majors")
def get_majors():
    return majors

@router.get("/creative-majors")
def get_creative_majors():
    return Creative_majors