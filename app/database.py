from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./ent_ai.db"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)