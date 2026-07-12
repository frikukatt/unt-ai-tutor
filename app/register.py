from fastapi import APIRouter
from app.users import User, users

router = APIRouter()

@router.post("/register")
def register_user(user: User):
    users.append(user)
    return {"message": "User registered successfully"}