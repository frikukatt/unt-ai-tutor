from fastapi import FastAPI
from app.routes import router
from app.register import router as register_router

from app.database import engine
from app.models import Base

from app.routes import router
from app.register import router as register_router
from app.login import router as login_router
from app.me import router as me_router
app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(router)
app.include_router(register_router)
app.include_router(login_router)
app.include_router(me_router)