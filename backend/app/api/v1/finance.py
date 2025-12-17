from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from fastapi_pagination import Page, paginate

from app.core.database import get_db_session
from app.schemas.finance import (
    Invoice, InvoiceCreate, InvoiceUpdate, InvoiceItem,
    Payment, PaymentCreate, PaymentLinkRequest, PaymentLinkResponse,
    FinancialReportRequest, AgingReportResponse, Service, ServiceCreate
)
from app.services.payment_service import PaymentService
from app.services.report_service import ReportService
from app.api.deps import get_current_active_user, get_current_admin

router = APIRouter(prefix="/finance", tags=["finance"])

# === ИНВОЙСЫ ===

@router.get("/invoices", response_model=Page[Invoice])
def read_invoices(
    db: Session = Depends(get_db_session),
    skip: int = 0,
    limit: int = 100,
    patient_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    overdue_only: bool = Query(False),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Получить список счетов с фильтрацией.
    """
    from app.models.finance import Invoice as InvoiceModel
    
    query = db.query(InvoiceModel)
    
    # Фильтры
    if patient_id:
        query = query.filter(InvoiceModel.patient_id == patient_id)
    
    if status:
        query = query.filter(InvoiceModel.status == status)
    
    if start_date:
        query = query.filter(InvoiceModel.issue_date >= start_date)
    
    if end_date:
        query = query.filter(InvoiceModel.issue_date <= end_date)
    
    if overdue_only:
        query = query.filter(InvoiceModel.is_overdue == True)
    
    query = query.order_by(InvoiceModel.issue_date.desc())
    
    invoices = query.offset(skip).limit(limit).all()
    return paginate(invoices)

@router.get("/invoices/{invoice_id}", response_model=Invoice)
def read_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Получить счет по ID.
    """
    from app.models.finance import Invoice as InvoiceModel
    
    invoice = db.query(InvoiceModel).get(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Счет не найден"
        )
    
    return invoice

@router.post("/invoices", response_model=Invoice, status_code=status.HTTP_201_CREATED)
def create_invoice(
    invoice_in: InvoiceCreate,
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_admin),
):
    """
    Создать новый счет.
    """
    from app.models.finance import Invoice as InvoiceModel, InvoiceItem as InvoiceItemModel
    
    # Генерируем номер счета
    from datetime import datetime
    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{db.query(InvoiceModel).count() + 1:04d}"
    
    # Создаем счет
    invoice = InvoiceModel(
        invoice_number=invoice_number,
        patient_id=invoice_in.patient_id,
        appointment_id=invoice_in.appointment_id,
        issue_date=date.today(),
        due_date=invoice_in.due_date,
        description=invoice_in.description,
        notes=invoice_in.notes,
        terms=invoice_in.terms,
        discount_percent=invoice_in.discount_percent or 0,
        tax_rate=invoice_in.tax_rate or 0
    )
    
    # Добавляем позиции
    for item_in in invoice_in.items:
        item = InvoiceItemModel(
            description=item_in.description,
            quantity=item_in.quantity,
            unit_price=item_in.unit_price,
            unit=item_in.unit,
            discount_percent=item_in.discount_percent or 0,
            discount_amount=item_in.discount_amount or 0,
            tax_rate=item_in.tax_rate or invoice_in.tax_rate or 0,
            service_id=item_in.service_id
        )
        invoice.items.append(item)
    
    # Рассчитываем итоги
    invoice.calculate_totals()
    
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    return invoice

@router.put("/invoices/{invoice_id}", response_model=Invoice)
def update_invoice(
    invoice_id: UUID,
    invoice_in: InvoiceUpdate,
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_admin),
):
    """
    Обновить счет.
    """
    from app.models.finance import Invoice as InvoiceModel
    
    invoice = db.query(InvoiceModel).get(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Счет не найден"
        )
    
    # Обновляем поля
    if invoice_in.due_date:
        invoice.due_date = invoice_in.due_date
    
    if invoice_in.status:
        invoice.status = invoice_in.status
    
    if invoice_in.notes is not None:
        invoice.notes = invoice_in.notes
    
    if invoice_in.terms is not None:
        invoice.terms = invoice_in.terms
    
    db.commit()
    db.refresh(invoice)
    
    return invoice

# === ПЛАТЕЖИ ===

@router.post("/payments", response_model=Payment, status_code=status.HTTP_201_CREATED)
def create_payment(
    payment_in: PaymentCreate,
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_admin),
):
    """
    Создать запись о платеже.
    """
    from app.models.finance import Payment as PaymentModel, Invoice as InvoiceModel
    
    # Проверяем счет
    invoice = db.query(InvoiceModel).get(payment_in.invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Счет не найден"
        )
    
    # Проверяем сумму
    if payment_in.amount > invoice.balance_due:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Сумма платежа превышает долг ({invoice.balance_due})"
        )
    
    # Создаем платеж
    payment = PaymentModel(
        invoice_id=payment_in.invoice_id,
        amount=payment_in.amount,
        payment_method=payment_in.payment_method,
        notes=payment_in.notes,
        reference_number=payment_in.reference_number
    )
    
    db.add(payment)
    
    # Обновляем счет
    invoice.add_payment(payment_in.amount, payment_in.payment_method, payment_in.notes)
    
    db.commit()
    db.refresh(payment)
    
    return payment

@router.post("/payment-link", response_model=PaymentLinkResponse)
def create_payment_link(
    link_request: PaymentLinkRequest,
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Создать ссылку для онлайн оплаты.
    """
    payment_service = PaymentService(db)
    
    try:
        result = payment_service.create_payment_link(
            invoice_id=str(link_request.invoice_id),
            amount=link_request.amount,
            success_url=link_request.success_url,
            cancel_url=link_request.cancel_url,
            description=link_request.description
        )
        
        return PaymentLinkResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания ссылки оплаты: {str(e)}"
        )

@router.post("/payment-webhook")
async def handle_payment_webhook(
    payload: Dict[str, Any],
    db: Session = Depends(get_db_session),
):
    """
    Вебхук для обработки уведомлений от платежной системы.
    """
    payment_service = PaymentService(db)
    
    success, message = payment_service.process_webhook(payload)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {"status": "ok", "message": message}

# === ОТЧЕТЫ ===

@router.post("/reports/financial")
def get_financial_report(
    report_request: FinancialReportRequest,
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_admin),
):
    """
    Получить финансовый отчет.
    """
    report_service = ReportService(db)
    
    report = report_service.get_financial_overview(
        start_date=report_request.start_date,
        end_date=report_request.end_date,
        group_by=report_request.group_by
    )
    
    return report

@router.get("/reports/aging", response_model=AgingReportResponse)
def get_aging_report(
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_admin),
):
    """
    Получить отчет по давности долгов.
    """
    report_service = ReportService(db)
    
    report = report_service.generate_aging_report()
    
    return AgingReportResponse(**report)

@router.get("/export/financial")
def export_financial_report(
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    format: str = Query("excel", regex="^(excel|csv)$"),
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_admin),
):
    """
    Экспортировать финансовый отчет.
    """
    report_service = ReportService(db)
    
    excel_file = report_service.export_to_excel(start_date, end_date, "financial")
    
    if format == "excel":
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=financial_report_{date.today()}.xlsx"}
        )
    else:
        # Конвертация в CSV
        import pandas as pd
        df = pd.read_excel(excel_file)
        csv_data = df.to_csv(index=False)
        
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=financial_report_{date.today()}.csv"}
        )

# === УСЛУГИ ===

@router.get("/services", response_model=List[Service])
def read_services(
    db: Session = Depends(get_db_session),
    category: Optional[str] = Query(None),
    active_only: bool = Query(True),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Получить список услуг.
    """
    from app.models.finance import Service as ServiceModel
    
    query = db.query(ServiceModel)
    
    if category:
        query = query.filter(ServiceModel.category == category)
    
    if active_only:
        query = query.filter(ServiceModel.is_active == True)
    
    services = query.order_by(ServiceModel.name).all()
    return services

@router.post("/services", response_model=Service, status_code=status.HTTP_201_CREATED)
def create_service(
    service_in: ServiceCreate,
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_admin),
):
    """
    Создать новую услугу.
    """
    from app.models.finance import Service as ServiceModel
    
    # Проверяем уникальность кода
    existing = db.query(ServiceModel).filter(ServiceModel.code == service_in.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Услуга с таким кодом уже существует"
        )
    
    service = ServiceModel(
        code=service_in.code,
        name=service_in.name,
        description=service_in.description,
        category=service_in.category,
        price=service_in.price,
        cost=service_in.cost,
        duration=service_in.duration,
        tax_rate=service_in.tax_rate,
        requires_doctor=service_in.requires_doctor,
        tags=service_in.tags or []
    )
    
    db.add(service)
    db.commit()
    db.refresh(service)
    
    return service