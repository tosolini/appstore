"""Database session + utilities"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.db.models import Base

# SQLite database path
DB_PATH = os.getenv('DB_PATH', '/app/data/appstore.db')

# Ensure directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Create engine
DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Crea tutte le tabelle se non esistono"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Dependency per FastAPI - ritorna sesione DB"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_sync() -> Session:
    """Ottieni sesione DB senza async (per background tasks)"""
    return SessionLocal()
