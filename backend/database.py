import os
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Added +psycopg2 explicitly to the driver string with connect_timeout=2
DATABASE_URL = "postgresql+psycopg2://postgres:admin@localhost:5432/kalki_db"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"connect_timeout": 2}
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
