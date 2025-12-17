import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import get_db_session
from app.models.base import Base

# Тестовая база данных
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Фикстура для БД
@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

# Фикстура для клиента
@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

# Тесты
def test_create_patient(client):
    """Тест создания пациента"""
    response = client.post(
        "/api/v1/patients/",
        json={
            "first_name": "Иван",
            "last_name": "Иванов",
            "phone": "+998934566336",
            "birth_date": "1990-01-01",
            "email": "ivan@example.com"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Иван"
    assert data["phone"] == "+998934566336"

def test_duplicate_phone(client):
    """Тест на дубликат телефона"""
    # Первый пациент
    client.post("/api/v1/patients/", json={
        "first_name": "Иван",
        "last_name": "Иванов",
        "phone": "+998934566336",
        "birth_date": "1990-01-01"
    })
    
    # Второй пациент с тем же телефоном
    response = client.post("/api/v1/patients/", json={
        "first_name": "Петр",
        "last_name": "Петров",
        "phone": "+998934566336",
        "birth_date": "1995-05-05"
    })
    
    assert response.status_code == 400
    assert "уже существует" in response.json()["detail"]