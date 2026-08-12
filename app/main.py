from fastapi import FastAPI
from app.routes import router
from app.register import router as register_router

from app.database import engine
from app.models import Base

from app.routes import router
from app.register import router as register_router
from app.login import router as login_router
from app.questions import router as questions_router
from app.profile import router as profile_router
from app.bookmarks import router as bookmarks_router
from app.categories import router as categories_router
app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(router)
app.include_router(register_router)
app.include_router(login_router)
app.include_router(questions_router)
app.include_router(profile_router)
app.include_router(bookmarks_router)
app.include_router(categories_router)