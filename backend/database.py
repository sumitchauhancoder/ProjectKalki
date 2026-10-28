import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment explicitly from backend/.env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

raw_url = os.getenv("DATABASE_URL")

# Resolve DB_CONNECT_TIMEOUT (default 10)
try:
    db_connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
except (ValueError, TypeError):
    db_connect_timeout = 10

if not raw_url or not raw_url.strip():
    # If DATABASE_URL is unset, use SQLite at backend/kalki.db so app runs with no server
    sqlite_path = (Path(__file__).resolve().parent / "kalki.db").as_posix()
    DATABASE_URL = f"sqlite:///{sqlite_path}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
elif raw_url.startswith("postgresql://") or raw_url.startswith("postgres://"):
    # If starts with postgresql://, use PostgreSQL (Neon). Add sslmode=require if missing.
    url = raw_url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    if "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"

    DATABASE_URL = url
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"connect_timeout": db_connect_timeout}
    )
elif raw_url.startswith("sqlite"):
    DATABASE_URL = raw_url
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    DATABASE_URL = raw_url
    engine = create_engine(DATABASE_URL, echo=False)

# Session factory and declarative base
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency that yields a session; yields None if connection fails."""
    db = None
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        print(f"[Database Error]: Connection attempt failed: {type(e).__name__}")
        yield None
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass
