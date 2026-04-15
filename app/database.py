from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Convert postgresql:// to postgresql+psycopg:// for the modern psycopg driver
_raw_db_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/testcase_db")
DATABASE_URL = _raw_db_url.replace("postgresql://", "postgresql+psycopg://", 1) if _raw_db_url.startswith("postgresql://") else _raw_db_url

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
