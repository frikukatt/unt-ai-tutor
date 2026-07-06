from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Welcome to ENT AI!"}

@app.get("/about")
def about():
    return {"message": "This project helps students prepare for UNT!"}