from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import app
from app.database import get_db
from app.models import User
from app.security import hash_password
from app.users import UserCreate

router = APIRouter()


@router.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):


    db_user = User(
        username=user.username,
        email=user.email,
        password=hash_password(user.password)
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {"message": "User registered successfully"}