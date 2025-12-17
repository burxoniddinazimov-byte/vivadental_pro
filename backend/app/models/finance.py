from sqlalchemy import Column, Numeric, String, ForeignKey, Enum, Boolean, Date, Text, Integer
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID, JSON
import uuid
import enum
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime

from .base import Base, TimestampMixin

class PaymentStatus(enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentMethod(enum.Enum):
    CASH = "cash"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    INSURANCE = "insurance"
    ONLINE = "online"
    TERMINAL = "terminal"
    CORPORATE = "corporate"

class TaxType(enum.Enum):
    NO_TAX = "no_tax"
    VAT_0 = "vat_0"
    VAT_10 = "vat_10"
    VAT_20 = "vat_20"
    SIMPLIFIED = "simplified"

class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"
    
    # Основные поля
    invoice_number = Column(String(50), unique=True, index=True, nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="SET NULL"))
    
    # Даты
    issue_date = Column(Date, nullable=False, default=date.today)
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date)
    
    # Суммы (ИСПРАВЛЯЮ float из vivag3.0 → Decimal)
    subtotal = Column(Numeric(10, 2), nullable=False, default=0)  # Без скидок и налогов
    discount_amount = Column(Numeric(10, 2), default=0)
    discount_percent = Column(Numeric(5, 2), default=0)
    tax_amount = Column(Numeric(10, 2), default=0)
    tax_rate = Column(Numeric(5, 2), default=0)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)  # Итог к оплате
    paid_amount = Column(Numeric(10, 2), default=0)
    
    # Статусы
    status = Column(Enum(PaymentStatus), default=PaymentStatus.DRAFT, index=True)
    payment_method = Column(Enum(PaymentMethod))
    
    # Детали
    description = Column(Text)
    notes = Column(Text)
    terms = Column(Text, default="Оплата в течение 10 дней")
    
    # Связи
    patient = relationship("Patient", back_populates="invoices")
    appointment = relationship("Appointment")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")
    
    # Валидаторы
    @validates('subtotal', 'discount_amount', 'tax_amount', 'total_amount', 'paid_amount')
    def validate_amounts(self, key, value):
        """Валидация денежных сумм (исправляю ошибки отрицательных сумм из vivag3.0)"""
        if value < 0:
            raise ValueError(f"{key} не может быть отрицательным")
        return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Вычисляемые свойства
    @property
    def balance_due(self) -> Decimal:
        """Остаток к оплате"""
        return (self.total_amount - self.paid_amount).quantize(Decimal('0.01'))
    
    @property
    def is_overdue(self) -> bool:
        """Просрочен ли счет"""
        if self.status == PaymentStatus.PAID:
            return False
        return self.due_date < date.today()
    
    @property
    def days_overdue(self) -> int:
        """Дней просрочки"""
        if not self.is_overdue:
            return 0
        return (date.today() - self.due_date).days
    
    # Методы
    def calculate_totals(self):
        """Пересчет итоговых сумм (исправляю ошибки расчета из vivag3.0)"""
        # Сумма по позициям
        self.subtotal = sum(item.total for item in self.items)
        
        # Скидка
        if self.discount_percent > 0:
            self.discount_amount = (self.subtotal * self.discount_percent / 100).quantize(Decimal('0.01'))
        
        # База для налога
        tax_base = self.subtotal - self.discount_amount
        
        # Налог
        if self.tax_rate > 0:
            self.tax_amount = (tax_base * self.tax_rate / 100).quantize(Decimal('0.01'))
        
        # Итог
        self.total_amount = (tax_base + self.tax_amount).quantize(Decimal('0.01'))
        
        # Обновляем статус
        self._update_status()
    
    def _update_status(self):
        """Обновление статуса счета"""
        if self.paid_amount == 0:
            self.status = PaymentStatus.PENDING
        elif self.paid_amount >= self.total_amount:
            self.status = PaymentStatus.PAID
            self.paid_date = date.today()
        elif self.paid_amount > 0:
            self.status = PaymentStatus.PARTIALLY_PAID
        
        if self.is_overdue and self.status != PaymentStatus.PAID:
            self.status = PaymentStatus.OVERDUE
    
    def add_payment(self, amount: Decimal, method: PaymentMethod, notes: str = None):
        """Добавление платежа (с транзакцией)"""
        amount = Decimal(amount).quantize(Decimal('0.01'))
        
        if amount <= 0:
            raise ValueError("Сумма платежа должна быть положительной")
        
        if amount > self.balance_due:
            raise ValueError("Сумма платежа превышает остаток долга")
        
        # Создаем запись платежа
        payment = Payment(
            invoice_id=self.id,
            amount=amount,
            payment_method=method,
            notes=notes
        )
        
        self.payments.append(payment)
        self.paid_amount += amount
        self._update_status()
        
        return payment

class InvoiceItem(Base, TimestampMixin):
    __tablename__ = "invoice_items"
    
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"))
    
    # Описание позиции
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False, default=1)  # Для поштучных и весовых товаров
    unit_price = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(20), default="шт.")
    
    # Скидка на позицию
    discount_percent = Column(Numeric(5, 2), default=0)
    discount_amount = Column(Numeric(10, 2), default=0)
    
    # Налог
    tax_rate = Column(Numeric(5, 2), default=0)
    tax_amount = Column(Numeric(10, 2), default=0)
    
    # Связи
    invoice = relationship("Invoice", back_populates="items")
    service = relationship("Service")
    
    # Вычисляемые свойства
    @property
    def subtotal(self) -> Decimal:
        """Сумма без скидок и налогов"""
        return (self.quantity * self.unit_price).quantize(Decimal('0.01'))
    
    @property
    def discount_total(self) -> Decimal:
        """Общая скидка на позицию"""
        if self.discount_percent > 0:
            discount = (self.subtotal * self.discount_percent / 100).quantize(Decimal('0.01'))
            return min(discount, self.discount_amount if self.discount_amount > 0 else discount)
        return self.discount_amount.quantize(Decimal('0.01'))
    
    @property
    def tax_base(self) -> Decimal:
        """База для расчета налога"""
        return (self.subtotal - self.discount_total).quantize(Decimal('0.01'))
    
    @property
    def tax_total(self) -> Decimal:
        """Сумма налога"""
        if self.tax_rate > 0:
            return (self.tax_base * self.tax_rate / 100).quantize(Decimal('0.01'))
        return Decimal('0.00')
    
    @property
    def total(self) -> Decimal:
        """Итоговая сумма позиции"""
        return (self.tax_base + self.tax_total).quantize(Decimal('0.01'))

class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    
    # Данные платежа
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    transaction_id = Column(String(100), unique=True, index=True)  # ID из платежной системы
    reference_number = Column(String(50))  # Номер чека или документа
    
    # Статус
    status = Column(String(20), default="completed")  # pending, completed, failed, refunded
    error_message = Column(Text)
    
    # Детали
    notes = Column(Text)
    metadata = Column(JSON)  # Дополнительные данные платежной системы
    
    # Связи
    invoice = relationship("Invoice", back_populates="payments")
    
    @validates('amount')
    def validate_amount(self, key, value):
        """Валидация суммы платежа"""
        if value <= 0:
            raise ValueError("Сумма платежа должна быть положительной")
        return Decimal(value).quantize(Decimal('0.01'))

class Service(Base, TimestampMixin):
    __tablename__ = "services"
    
    # Основные данные
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)
    
    # Цены
    price = Column(Numeric(10, 2), nullable=False)
    cost = Column(Numeric(10, 2))  # Себестоимость
    duration = Column(Integer)  # Длительность в минутах
    
    # Налоги и учет
    tax_rate = Column(Numeric(5, 2), default=0)
    is_active = Column(Boolean, default=True)
    requires_doctor = Column(Boolean, default=True)
    
    # Дополнительно
    tags = Column(ARRAY(String), default=list)
    metadata = Column(JSON)
    
    # Связи
    invoice_items = relationship("InvoiceItem", back_populates="service")

class InsuranceContract(Base, TimestampMixin):
    __tablename__ = "insurance_contracts"
    
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    insurance_company = Column(String(200), nullable=False)
    contract_number = Column(String(100), nullable=False, unique=True, index=True)
    
    # Даты
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Лимиты
    annual_limit = Column(Numeric(10, 2))
    remaining_limit = Column(Numeric(10, 2))
    visit_limit = Column(Integer)
    remaining_visits = Column(Integer)
    
    # Детали
    coverage_details = Column(JSON)
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Связи
    patient = relationship("Patient")
    claims = relationship("InsuranceClaim", back_populates="contract")

class InsuranceClaim(Base, TimestampMixin):
    __tablename__ = "insurance_claims"
    
    contract_id = Column(UUID(as_uuid=True), ForeignKey("insurance_contracts.id", ondelete="CASCADE"), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="SET NULL"))
    
    # Данные заявки
    claim_number = Column(String(100), unique=True, index=True)
    amount_claimed = Column(Numeric(10, 2), nullable=False)
    amount_approved = Column(Numeric(10, 2))
    
    # Статус
    status = Column(String(50), default="submitted")  # submitted, approved, paid, rejected
    submission_date = Column(Date, default=date.today)
    decision_date = Column(Date)
    
    # Документы
    documents = Column(JSON)  # Ссылки на документы
    notes = Column(Text)
    
    # Связи
    contract = relationship("InsuranceContract", back_populates="claims")
    invoice = relationship("Invoice")