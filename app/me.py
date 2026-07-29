from fastapi import APIRouter, Depends

from app.models import User
from app.security import get_current_user

router = APIRouter()


@router.get("/me")
def read_me(current_user: User = Depends(get_current_user)):
    return current_user