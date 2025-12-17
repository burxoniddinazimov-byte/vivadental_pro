from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from .config import settings

# Исправляю ошибку пула соединений из vivag3.0
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,  # Оптимальный размер пула
    max_overflow=30,  # Максимальное количество соединений сверх pool_size
    pool_pre_ping=True,  # Проверка соединения перед использованием
    echo=False  # В продакшене False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Контекстный менеджер для сессий БД (исправляю утечки соединений)"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# Dependency для FastAPI
def get_db_session():
    with get_db() as db:
        yield db