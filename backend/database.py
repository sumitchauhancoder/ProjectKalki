import os
import re
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

# Pull from environment variables, fallback to local if missing
raw_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:admin@localhost:5432/kalki_db")

# Ensure SQLAlchemy uses the psycopg2 driver format for Neon/Postgres
if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif raw_url.startswith("postgresql://") and "+psycopg2" not in raw_url:
    raw_url = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)

DATABASE_URL = raw_url

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={
        "connect_timeout": 5
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = None
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        print(f"[Database Connection Warning]: {e}")
        yield None
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass