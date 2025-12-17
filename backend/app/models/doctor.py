from sqlalchemy import Column, String, JSON, Boolean, Time, Interval
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base, TimestampMixin

class Doctor(Base, TimestampMixin):
    __tablename__ = "doctors"
    
    # Основная информация
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100))
    specialization = Column(String(200), nullable=False)
    
    # Контакты
    phone = Column(String(20), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    
    # Расписание (исправляю жесткую привязку из VIVAD)
    work_schedule = Column(JSON, default=lambda: {
        "monday": {"start": "09:00", "end": "18:00", "break": "13:00-14:00"},
        "tuesday": {"start": "09:00", "end": "18:00", "break": "13:00-14:00"},
        "wednesday": {"start": "09:00", "end": "18:00", "break": "13:00-14:00"},
        "thursday": {"start": "09:00", "end": "18:00", "break": "13:00-14:00"},
        "friday": {"start": "09:00", "end": "18:00", "break": "13:00-14:00"},
        "saturday": {"start": "10:00", "end": "16:00", "break": None},
        "sunday": {"start": None, "end": None, "break": None}
    })
    
    # Настройки
    appointment_duration = Column(Interval, default='00:30:00')  # 30 минут по умолчанию
    max_patients_per_day = Column(Integer, default=20)
    is_active = Column(Boolean, default=True)
    
    # Дополнительная информация
    license_number = Column(String(50))
    qualifications = Column(ARRAY(String), default=list)
    notes = Column(Text)
    
    # Связи
    appointments = relationship("Appointment", back_populates="doctor", 
                               cascade="all, delete-orphan")
    
    # Методы для работы с расписанием
    def is_available_on_day(self, day_of_week: str) -> bool:
        """Проверка работы врача в конкретный день"""
        schedule = self.work_schedule.get(day_of_week.lower())
        return schedule and schedule.get("start") and schedule.get("end")
    
    def get_work_hours(self, day_of_week: str) -> tuple:
        """Получение рабочего времени на день"""
        schedule = self.work_schedule.get(day_of_week.lower())
        if not schedule:
            return None, None
        return schedule.get("start"), schedule.get("end")