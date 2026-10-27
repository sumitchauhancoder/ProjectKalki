import os
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Added +psycopg2 explicitly to the driver string
DATABASE_URL = "postgresql+psycopg2://postgres:admin@localhost:5432/kalki_db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()