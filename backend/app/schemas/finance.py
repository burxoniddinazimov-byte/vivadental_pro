from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from uuid import UUID
from decimal import Decimal
import enum

from app.models.finance import PaymentStatus, PaymentMethod, TaxType

class InvoiceItemBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal = Field(default=1, ge=0.001, le=10000)
    unit_price: Decimal = Field(..., ge=0, le=1000000)
    unit: str = Field(default="шт.")
    discount_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    tax_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    service_id: Optional[UUID] = None

class InvoiceItemCreate(InvoiceItemBase):
    @validator('unit_price', 'quantity', 'discount_percent', 
               'discount_amount', 'tax_rate', pre=True)
    def validate_decimals(cls, v):
        """Валидация decimal значений"""
        if v is None:
            return v
        try:
            return Decimal(str(v)).quantize(Decimal('0.01'))
        except:
            raise ValueError("Некорректное числовое значение")

class InvoiceItem(InvoiceItemBase):
    id: UUID
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class InvoiceBase(BaseModel):
    patient_id: UUID
    appointment_id: Optional[UUID] = None
    due_date: date
    description: Optional[str] = None
    notes: Optional[str] = None
    terms: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate]
    discount_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    tax_rate: Optional[Decimal] = Field(default=0, ge=0, le=100)

class InvoiceUpdate(BaseModel):
    due_date: Optional[date] = None
    status: Optional[PaymentStatus] = None
    notes: Optional[str] = None
    terms: Optional[str] = None

class Invoice(InvoiceBase):
    id: UUID
    invoice_number: str
    issue_date: date
    subtotal: Decimal
    discount_amount: Decimal
    discount_percent: Decimal
    tax_amount: Decimal
    tax_rate: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    status: PaymentStatus
    payment_method: Optional[PaymentMethod] = None
    paid_date: Optional[date] = None
    is_overdue: bool
    days_overdue: int
    items: List[InvoiceItem]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PaymentBase(BaseModel):
    invoice_id: UUID
    amount: Decimal = Field(..., gt=0, le=1000000)
    payment_method: PaymentMethod
    notes: Optional[str] = None
    reference_number: Optional[str] = None

class PaymentCreate(PaymentBase):
    @validator('amount', pre=True)
    def validate_amount(cls, v):
        return Decimal(str(v)).quantize(Decimal('0.01'))

class Payment(PaymentBase):
    id: UUID
    transaction_id: Optional[str] = None
    status: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PaymentLinkRequest(BaseModel):
    invoice_id: UUID
    amount: Optional[Decimal] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    description: Optional[str] = None

class PaymentLinkResponse(BaseModel):
    payment_id: str
    amount: Decimal
    confirmation_url: str
    invoice_number: str

class FinancialReportRequest(BaseModel):
    start_date: date
    end_date: date = Field(default_factory=date.today)
    group_by: str = Field(default="day", pattern="^(day|week|month|doctor|service)$")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('Дата окончания должна быть позже даты начала')
        if (v - values['start_date']).days > 365:
            raise ValueError('Максимальный период - 1 год')
        return v

class AgingReportResponse(BaseModel):
    report_date: date
    aging_summary: List[Dict[str, Any]]
    top_debtors: List[Dict[str, Any]]

class ServiceBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    price: Decimal = Field(..., ge=0, le=1000000)
    cost: Optional[Decimal] = None
    duration: Optional[int] = Field(None, ge=1, le=480)
    tax_rate: Decimal = Field(default=0, ge=0, le=100)
    requires_doctor: bool = True
    tags: Optional[List[str]] = None

class ServiceCreate(ServiceBase):
    pass

class Service(ServiceBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)