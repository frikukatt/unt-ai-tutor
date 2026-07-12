from fastapi import FastAPI
from app.routes import router
from app.register import router as register_router

app = FastAPI()

app.include_router(router)
app.include_router(register_router)