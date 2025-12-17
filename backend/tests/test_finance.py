import pytest
from decimal import Decimal
from datetime import date, timedelta

def test_create_invoice(client, db_session):
    """Тест создания счета"""
    # Создаем пациента
    patient = create_test_patient(db_session)
    
    # Создаем счет
    response = client.post(
        "/api/v1/finance/invoices",
        json={
            "patient_id": str(patient.id),
            "due_date": (date.today() + timedelta(days=10)).isoformat(),
            "description": "Лечение кариеса",
            "items": [
                {
                    "description": "Консультация",
                    "quantity": 1,
                    "unit_price": 1500.00,
                    "tax_rate": 20
                },
                {
                    "description": "Пломба",
                    "quantity": 1,
                    "unit_price": 3500.00,
                    "tax_rate": 20
                }
            ],
            "discount_percent": 10,
            "tax_rate": 20
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    
    # Проверяем расчеты
    assert data["subtotal"] == "5000.00"  # 1500 + 3500
    assert data["discount_amount"] == "500.00"  # 10% от 5000
    assert data["tax_amount"] == "900.00"  # 20% от 4500 (5000-500)
    assert data["total_amount"] == "5400.00"  # 4500 + 900

def test_payment_processing(client, db_session):
    """Тест обработки платежа"""
    # Создаем счет
    invoice = create_test_invoice(db_session)
    
    # Создаем платеж
    response = client.post(
        "/api/v1/finance/payments",
        json={
            "invoice_id": str(invoice.id),
            "amount": 2000.00,
            "payment_method": "cash",
            "notes": "Частичная оплата"
        }
    )
    
    assert response.status_code == 201
    
    # Проверяем обновление счета
    response = client.get(f"/api/v1/finance/invoices/{invoice.id}")
    data = response.json()
    
    assert data["paid_amount"] == "2000.00"
    assert data["balance_due"] == "3400.00"  # 5400 - 2000
    assert data["status"] == "partially_paid"

def test_overdue_invoice(client, db_session):
    """Тест просроченного счета"""
    invoice = create_test_invoice(db_session)
    
    # Устанавливаем просроченную дату
    from app.models.finance import Invoice as InvoiceModel
    invoice.due_date = date.today() - timedelta(days=10)
    db_session.commit()
    
    response = client.get(f"/api/v1/finance/invoices/{invoice.id}")
    data = response.json()
    
    assert data["is_overdue"] == True
    assert data["days_overdue"] == 10
    assert data["status"] == "overdue"

def test_aging_report(client, db_session):
    """Тест отчета по давности долгов"""
    response = client.get("/api/v1/finance/reports/aging")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "report_date" in data
    assert "aging_summary" in data
    assert "top_debtors" in data

def test_service_management(client, db_session):
    """Тест управления услугами"""
    # Создаем услугу
    response = client.post(
        "/api/v1/finance/services",
        json={
            "code": "CONSULT",
            "name": "Консультация стоматолога",
            "category": "Консультации",
            "price": 1500.00,
            "duration": 30,
            "tax_rate": 20
        }
    )
    
    assert response.status_code == 201
    
    # Получаем список услуг
    response = client.get("/api/v1/finance/services")
    assert response.status_code == 200
    services = response.json()
    assert len(services) > 0
    assert services[0]["code"] == "CONSULT"