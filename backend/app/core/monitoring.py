from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from prometheus_client.exposition import MetricsHandler
import time
from functools import wraps
from fastapi import Request, Response
from typing import Callable

# Метрики для запросов
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

ACTIVE_REQUESTS = Gauge(
    'http_requests_active',
    'Active HTTP requests'
)

# Метрики для базы данных
DB_QUERY_COUNT = Counter(
    'db_queries_total',
    'Total database queries',
    ['operation', 'table']
)

DB_QUERY_DURATION = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['operation', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

# Метрики для бизнес-логики
PATIENT_COUNT = Gauge(
    'patients_total',
    'Total number of patients'
)

APPOINTMENT_COUNT = Gauge(
    'appointments_total',
    'Total number of appointments',
    ['status']
)

REVENUE_TOTAL = Gauge(
    'revenue_total',
    'Total revenue'
)

def monitor_request(func: Callable):
    """Декоратор для мониторинга HTTP запросов"""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        start_time = time.time()
        ACTIVE_REQUESTS.inc()
        
        try:
            response = await func(request, *args, **kwargs)
            
            # Логируем запрос
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()
            
            return response
            
        finally:
            duration = time.time() - start_time
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
            ACTIVE_REQUESTS.dec()
    
    return wrapper

def monitor_db_query(operation: str, table: str):
    """Декоратор для мониторинга запросов к БД"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                DB_QUERY_COUNT.labels(operation=operation, table=table).inc()
                DB_QUERY_DURATION.labels(operation=operation, table=table).observe(duration)
        
        return wrapper
    return decorator

def update_business_metrics(db):
    """Обновление бизнес-метрик"""
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.models.finance import Invoice
    
    try:
        # Количество пациентов
        patient_count = db.query(Patient).filter(Patient.is_active == True).count()
        PATIENT_COUNT.set(patient_count)
        
        # Количество записей по статусам
        from sqlalchemy import func
        status_counts = db.query(
            Appointment.status,
            func.count(Appointment.id)
        ).group_by(Appointment.status).all()
        
        for status, count in status_counts:
            APPOINTMENT_COUNT.labels(status=status).set(count)
        
        # Общая выручка
        total_revenue = db.query(func.sum(Invoice.total_amount)).scalar() or 0
        REVENUE_TOTAL.set(float(total_revenue))
        
    except Exception as e:
        # Логируем ошибку, но не падаем
        print(f"Error updating metrics: {e}")

class MetricsEndpoint:
    """Endpoint для Prometheus метрик"""
    @staticmethod
    async def get_metrics():
        """Возвращает метрики в формате Prometheus"""
        return Response(
            content=generate_latest(REGISTRY),
            media_type="text/plain"
        )