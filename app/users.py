from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    