from sqlalchemy import Column, String, Date, Boolean, Text, ForeignKey, ARRAY, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base, TimestampMixin

class Patient(Base, TimestampMixin):
    __tablename__ = "patients"
    
    # Основная информация
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100))
    
    # Контакты (исправляю ошибку из vivag3.0 - было одно поле для всего)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True)
    telegram = Column(String(100))
    whatsapp = Column(String(20))
    
    # Демографические данные
    birth_date = Column(Date, nullable=False)
    gender = Column(String(10))  # male/female/other
    blood_group = Column(String(5))
    
    # Адрес (структурировано, а не текстом как в VIVAD)
    address_json = Column(JSON, default=lambda: {
        "street": "",
        "city": "",
        "postal_code": "",
        "country": "Россия"
    })
    
    # Медицинская информация
    allergies = Column(ARRAY(String), default=list)
    chronic_diseases = Column(ARRAY(String), default=list)
    medications = Column(ARRAY(String), default=list)
    
    # Документы
    passport_number = Column(String(50))
    insurance_number = Column(String(50))
    snils = Column(String(14))  # СНИЛС
    
    # Статус
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    
    # Связи (исправляю ошибку из Vivad2.0 - не было каскадного удаления)
    appointments = relationship("Appointment", back_populates="patient", 
                               cascade="all, delete-orphan")
    medical_records = relationship("MedicalRecord", back_populates="patient",
                                   cascade="all, delete-orphan")
    financial_records = relationship("FinancialRecord", back_populates="patient",
                                     cascade="all, delete-orphan")
    
    # Индексы для быстрого поиска (не было в предыдущих версиях)
    __table_args__ = (
        Index('ix_patients_full_name', 'last_name', 'first_name'),
        Index('ix_patients_birth_date', 'birth_date'),
    )